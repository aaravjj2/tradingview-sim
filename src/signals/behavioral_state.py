"""
Behavioral State Machine

Implements hysteresis, cooldown, and phased re-entry logic
to ensure predictable and boring trading behavior.

Features:
- N_exit_confirm: Require N consecutive days to confirm exit
- M_reentry_confirm: Require M consecutive days to confirm re-entry
- cooldown_days: Disable re-entry for X days after exit
- phased_reentry_steps: Ramp exposure gradually during re-entry
"""

import os
import yaml
from datetime import date, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from collections import deque


class MarketState(Enum):
    """Current market position state."""
    OUT = "out"           # Not in market
    ENTERING = "entering" # Phased entry in progress
    IN = "in"             # Fully in market
    EXITING = "exiting"   # Confirming exit
    COOLDOWN = "cooldown" # Post-exit waiting period


@dataclass
class BehavioralConfig:
    """Configuration for behavioral state machine."""
    N_exit_confirm: int = 3
    M_reentry_confirm: int = 2
    cooldown_days: int = 5
    rolling_conf_window: int = 10
    phased_reentry_steps: List[float] = field(default_factory=lambda: [0.25, 0.5, 1.0])
    enable_hysteresis: bool = True
    enable_cooldown: bool = True
    enable_phased_reentry: bool = True
    
    @classmethod
    def from_yaml(cls, config_path: str) -> "BehavioralConfig":
        """Load config from YAML file."""
        if not os.path.exists(config_path):
            return cls()
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        behavioral = config.get("behavioral", {})
        return cls(
            N_exit_confirm=behavioral.get("N_exit_confirm", 3),
            M_reentry_confirm=behavioral.get("M_reentry_confirm", 2),
            cooldown_days=behavioral.get("cooldown_days", 5),
            rolling_conf_window=behavioral.get("rolling_conf_window", 10),
            phased_reentry_steps=behavioral.get("phased_reentry_steps", [0.25, 0.5, 1.0]),
            enable_hysteresis=behavioral.get("enable_hysteresis", True),
            enable_cooldown=behavioral.get("enable_cooldown", True),
            enable_phased_reentry=behavioral.get("enable_phased_reentry", True),
        )


@dataclass
class DecisionLog:
    """Log entry for decision transparency."""
    date: str
    raw_signal: int
    filtered_signal: int
    exposure: float
    state: MarketState
    reason: str
    recent_vol_values: List[float]
    rolling_confidence: float
    days_in_state: int


class BehavioralStateMachine:
    """
    State machine managing entry/exit hysteresis, cooldown, and phased re-entry.
    
    Designed for predictable, boring behavior with minimized whipsaw.
    """
    
    def __init__(self, config: Optional[BehavioralConfig] = None):
        self.config = config or BehavioralConfig()
        
        # State tracking
        self.state = MarketState.OUT
        self.days_in_state = 0
        self.exit_confirm_count = 0
        self.entry_confirm_count = 0
        self.cooldown_remaining = 0
        self.phased_entry_step = 0
        self.last_exit_date: Optional[date] = None
        
        # History tracking
        self.confidence_history: deque = deque(maxlen=self.config.rolling_conf_window)
        self.volatility_history: deque = deque(maxlen=10)
        self.decision_log: List[DecisionLog] = []
        
    def _get_rolling_confidence(self) -> float:
        """Calculate rolling average confidence."""
        if not self.confidence_history:
            return 0.5
        return sum(self.confidence_history) / len(self.confidence_history)
    
    def _get_recent_vol_values(self) -> List[float]:
        """Get recent volatility values for logging."""
        return list(self.volatility_history)
    
    def _log_decision(self, current_date: str, raw_signal: int, filtered_signal: int,
                      exposure: float, reason: str):
        """Log decision for transparency."""
        log_entry = DecisionLog(
            date=current_date,
            raw_signal=raw_signal,
            filtered_signal=filtered_signal,
            exposure=exposure,
            state=self.state,
            reason=reason,
            recent_vol_values=self._get_recent_vol_values(),
            rolling_confidence=self._get_rolling_confidence(),
            days_in_state=self.days_in_state,
        )
        self.decision_log.append(log_entry)
        
        # Keep log bounded
        if len(self.decision_log) > 500:
            self.decision_log = self.decision_log[-250:]
    
    def process_signal(self, raw_signal: int, confidence: float, 
                       volatility: float, current_date: str) -> Tuple[int, float]:
        """
        Process raw signal through behavioral filters.
        
        Args:
            raw_signal: Raw model signal (-1 = exit, 0 = neutral, 1 = enter)
            confidence: Model confidence (0-1)
            volatility: Current volatility estimate
            current_date: Current date string (YYYY-MM-DD)
            
        Returns:
            (filtered_signal, exposure): Filtered signal and position exposure
        """
        # Update history
        self.confidence_history.append(confidence)
        self.volatility_history.append(volatility)
        
        # Increment days in current state
        self.days_in_state += 1
        
        # Decrement cooldown if active
        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1
        
        # Default exposure
        base_exposure = 0.3  # Default from model
        
        # Process based on current state
        if self.state == MarketState.OUT:
            return self._handle_out_state(raw_signal, confidence, current_date, base_exposure)
        elif self.state == MarketState.COOLDOWN:
            return self._handle_cooldown_state(raw_signal, confidence, current_date, base_exposure)
        elif self.state == MarketState.ENTERING:
            return self._handle_entering_state(raw_signal, confidence, current_date, base_exposure)
        elif self.state == MarketState.IN:
            return self._handle_in_state(raw_signal, confidence, current_date, base_exposure)
        elif self.state == MarketState.EXITING:
            return self._handle_exiting_state(raw_signal, confidence, current_date, base_exposure)
        
        return (0, 0.0)  # Fallback
    
    def _handle_out_state(self, raw_signal: int, confidence: float, 
                          current_date: str, base_exposure: float) -> Tuple[int, float]:
        """Handle OUT state - waiting for entry signal."""
        if raw_signal == 1:
            if self.config.enable_hysteresis:
                self.entry_confirm_count += 1
                if self.entry_confirm_count >= self.config.M_reentry_confirm:
                    # Confirmed entry
                    self._transition_to(MarketState.ENTERING if self.config.enable_phased_reentry 
                                        else MarketState.IN)
                    self.entry_confirm_count = 0
                    exposure = self._get_phased_exposure(base_exposure)
                    self._log_decision(current_date, raw_signal, 1, exposure,
                                      f"Entry confirmed after {self.config.M_reentry_confirm} days")
                    return (1, exposure)
                else:
                    self._log_decision(current_date, raw_signal, 0, 0.0,
                                      f"Entry pending confirmation ({self.entry_confirm_count}/{self.config.M_reentry_confirm})")
                    return (0, 0.0)
            else:
                # No hysteresis - immediate entry
                self._transition_to(MarketState.IN)
                self._log_decision(current_date, raw_signal, 1, base_exposure,
                                  "Immediate entry (hysteresis disabled)")
                return (1, base_exposure)
        else:
            self.entry_confirm_count = 0
            self._log_decision(current_date, raw_signal, 0, 0.0, "No entry signal")
            return (0, 0.0)
    
    def _handle_cooldown_state(self, raw_signal: int, confidence: float,
                               current_date: str, base_exposure: float) -> Tuple[int, float]:
        """Handle COOLDOWN state - post-exit waiting period."""
        if self.cooldown_remaining <= 0:
            self._transition_to(MarketState.OUT)
            self._log_decision(current_date, raw_signal, 0, 0.0,
                              "Cooldown complete, transitioning to OUT")
            # Re-process as OUT state
            return self._handle_out_state(raw_signal, confidence, current_date, base_exposure)
        
        # Still in cooldown
        self._log_decision(current_date, raw_signal, 0, 0.0,
                          f"Cooldown active ({self.cooldown_remaining} days remaining)")
        return (0, 0.0)
    
    def _handle_entering_state(self, raw_signal: int, confidence: float,
                               current_date: str, base_exposure: float) -> Tuple[int, float]:
        """Handle ENTERING state - phased entry in progress."""
        if raw_signal == -1:
            # Exit signal during entry - abort
            if self.config.enable_cooldown:
                self._transition_to(MarketState.COOLDOWN)
                self.cooldown_remaining = self.config.cooldown_days
            else:
                self._transition_to(MarketState.OUT)
            self.phased_entry_step = 0
            self._log_decision(current_date, raw_signal, -1, 0.0,
                              "Entry aborted - exit signal received")
            return (-1, 0.0)
        
        # Continue phased entry
        self.phased_entry_step = min(self.phased_entry_step + 1, 
                                     len(self.config.phased_reentry_steps) - 1)
        exposure = self._get_phased_exposure(base_exposure)
        
        if self.phased_entry_step >= len(self.config.phased_reentry_steps) - 1:
            self._transition_to(MarketState.IN)
            self._log_decision(current_date, raw_signal, 1, exposure,
                              "Phased entry complete")
        else:
            self._log_decision(current_date, raw_signal, 1, exposure,
                              f"Phased entry step {self.phased_entry_step + 1}/{len(self.config.phased_reentry_steps)}")
        
        return (1, exposure)
    
    def _handle_in_state(self, raw_signal: int, confidence: float,
                         current_date: str, base_exposure: float) -> Tuple[int, float]:
        """Handle IN state - fully in market."""
        if raw_signal == -1:
            if self.config.enable_hysteresis:
                self.exit_confirm_count += 1
                if self.exit_confirm_count >= self.config.N_exit_confirm:
                    # Confirmed exit
                    self._execute_exit(current_date)
                    self._log_decision(current_date, raw_signal, -1, 0.0,
                                      f"Exit confirmed after {self.config.N_exit_confirm} days")
                    return (-1, 0.0)
                else:
                    # Pending confirmation - stay in but log warning
                    self._transition_to(MarketState.EXITING)
                    self._log_decision(current_date, raw_signal, 1, base_exposure,
                                      f"Exit pending ({self.exit_confirm_count}/{self.config.N_exit_confirm})")
                    return (1, base_exposure)
            else:
                # No hysteresis - immediate exit
                self._execute_exit(current_date)
                self._log_decision(current_date, raw_signal, -1, 0.0,
                                  "Immediate exit (hysteresis disabled)")
                return (-1, 0.0)
        else:
            self.exit_confirm_count = 0
            self._log_decision(current_date, raw_signal, 1, base_exposure, "Staying in market")
            return (1, base_exposure)
    
    def _handle_exiting_state(self, raw_signal: int, confidence: float,
                              current_date: str, base_exposure: float) -> Tuple[int, float]:
        """Handle EXITING state - confirming exit."""
        if raw_signal == -1:
            self.exit_confirm_count += 1
            if self.exit_confirm_count >= self.config.N_exit_confirm:
                self._execute_exit(current_date)
                self._log_decision(current_date, raw_signal, -1, 0.0,
                                  f"Exit confirmed after {self.config.N_exit_confirm} days")
                return (-1, 0.0)
            else:
                self._log_decision(current_date, raw_signal, 1, base_exposure,
                                  f"Exit pending ({self.exit_confirm_count}/{self.config.N_exit_confirm})")
                return (1, base_exposure)
        else:
            # Exit signal cancelled - back to IN
            self.exit_confirm_count = 0
            self._transition_to(MarketState.IN)
            self._log_decision(current_date, raw_signal, 1, base_exposure,
                              "Exit cancelled - signal reversed")
            return (1, base_exposure)
    
    def _transition_to(self, new_state: MarketState):
        """Transition to new state."""
        self.state = new_state
        self.days_in_state = 0
    
    def _execute_exit(self, current_date: str):
        """Execute exit and start cooldown."""
        if self.config.enable_cooldown:
            self._transition_to(MarketState.COOLDOWN)
            self.cooldown_remaining = self.config.cooldown_days
        else:
            self._transition_to(MarketState.OUT)
        self.exit_confirm_count = 0
        self.phased_entry_step = 0
    
    def _get_phased_exposure(self, base_exposure: float) -> float:
        """Get exposure based on phased entry step."""
        if not self.config.enable_phased_reentry:
            return base_exposure
        
        step_idx = min(self.phased_entry_step, len(self.config.phased_reentry_steps) - 1)
        return base_exposure * self.config.phased_reentry_steps[step_idx]
    
    def get_state_summary(self) -> Dict:
        """Get current state summary for debugging."""
        return {
            "state": self.state.value,
            "days_in_state": self.days_in_state,
            "exit_confirm_count": self.exit_confirm_count,
            "entry_confirm_count": self.entry_confirm_count,
            "cooldown_remaining": self.cooldown_remaining,
            "phased_entry_step": self.phased_entry_step,
            "rolling_confidence": self._get_rolling_confidence(),
        }
    
    def reset(self):
        """Reset state machine to initial state."""
        self.state = MarketState.OUT
        self.days_in_state = 0
        self.exit_confirm_count = 0
        self.entry_confirm_count = 0
        self.cooldown_remaining = 0
        self.phased_entry_step = 0
        self.last_exit_date = None
        self.confidence_history.clear()
        self.volatility_history.clear()
        self.decision_log.clear()


# Module-level singleton for stateful operation
_state_machine: Optional[BehavioralStateMachine] = None


def get_state_machine(config_path: str = None) -> BehavioralStateMachine:
    """Get or create the behavioral state machine singleton."""
    global _state_machine
    
    if _state_machine is None:
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "configs", "config.volgate.yaml"
            )
        config = BehavioralConfig.from_yaml(config_path)
        _state_machine = BehavioralStateMachine(config)
    
    return _state_machine


def reset_state_machine():
    """Reset the singleton state machine."""
    global _state_machine
    if _state_machine:
        _state_machine.reset()
    _state_machine = None
