"""
TWAP (Time-Weighted Average Price) Execution Algorithm
Drip orders over time to minimize market impact
"""

import asyncio
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import random
import math


class TWAPExecutor:
    """
    Time-Weighted Average Price (TWAP) Execution
    
    Splits a large order into smaller child orders executed at regular intervals
    to minimize market impact and achieve a price close to the TWAP.
    
    Features:
    - Randomized slice sizes (within bounds) to avoid detection
    - Randomized execution timing (within intervals)
    - Volume participation limits
    - Cancel/pause functionality
    """
    
    def __init__(
        self,
        ticker: str,
        side: str,  # 'buy' or 'sell'
        total_quantity: int,
        duration_minutes: int = 60,
        num_slices: int = 10,
        randomize_size: bool = True,  # Random slice sizes
        randomize_timing: bool = True,  # Random execution within windows
        max_slice_pct: float = 0.20,  # Max 20% of total in one slice
        paper_mode: bool = True
    ):
        self.ticker = ticker
        self.side = side
        self.total_quantity = total_quantity
        self.duration_minutes = duration_minutes
        self.num_slices = num_slices
        self.randomize_size = randomize_size
        self.randomize_timing = randomize_timing
        self.max_slice_pct = max_slice_pct
        self.paper_mode = paper_mode
        
        # Execution state
        self.is_running = False
        self.is_paused = False
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Progress tracking
        self.executed_quantity = 0
        self.executed_slices: List[Dict] = []
        self.remaining_quantity = total_quantity
        self.avg_execution_price = 0.0
        self.total_cost = 0.0
        
        # Generate slice schedule
        self.slice_schedule = self._generate_slice_schedule()
        self.current_slice_index = 0
    
    def _generate_slice_schedule(self) -> List[Dict]:
        """Generate the execution schedule with slice sizes and times"""
        slices = []
        interval_seconds = (self.duration_minutes * 60) / self.num_slices
        base_slice_size = self.total_quantity / self.num_slices
        max_slice_size = int(self.total_quantity * self.max_slice_pct)
        
        remaining = self.total_quantity
        
        for i in range(self.num_slices):
            # Calculate slice size
            if self.randomize_size and i < self.num_slices - 1:
                # Random size between 50% and 150% of base, capped at max
                min_size = max(1, int(base_slice_size * 0.5))
                max_size = min(int(base_slice_size * 1.5), max_slice_size, remaining)
                slice_size = random.randint(min_size, max_size)
            else:
                # Last slice gets the remainder
                slice_size = remaining
            
            slice_size = min(slice_size, remaining)
            remaining -= slice_size
            
            # Calculate execution time
            base_time = i * interval_seconds
            if self.randomize_timing:
                # Random offset within the interval window (up to 80% of interval)
                time_offset = random.uniform(0, interval_seconds * 0.8)
                exec_time = base_time + time_offset
            else:
                exec_time = base_time
            
            slices.append({
                "slice_index": i,
                "quantity": slice_size,
                "scheduled_seconds": exec_time,
                "status": "pending"
            })
        
        return slices
    
    def start(self):
        """Start the TWAP execution"""
        self.is_running = True
        self.is_paused = False
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(minutes=self.duration_minutes)
    
    def pause(self):
        """Pause execution"""
        self.is_paused = True
    
    def resume(self):
        """Resume execution"""
        self.is_paused = False
    
    def cancel(self):
        """Cancel remaining execution"""
        self.is_running = False
        for slice_info in self.slice_schedule:
            if slice_info["status"] == "pending":
                slice_info["status"] = "cancelled"
    
    def get_progress(self) -> Dict:
        """Get execution progress"""
        pct_complete = (self.executed_quantity / self.total_quantity * 100) if self.total_quantity > 0 else 0
        
        elapsed = 0
        remaining_time = self.duration_minutes * 60
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            remaining_time = max(0, self.duration_minutes * 60 - elapsed)
        
        return {
            "ticker": self.ticker,
            "side": self.side,
            "total_quantity": self.total_quantity,
            "executed_quantity": self.executed_quantity,
            "remaining_quantity": self.remaining_quantity,
            "pct_complete": round(pct_complete, 1),
            "avg_price": round(self.avg_execution_price, 4),
            "total_cost": round(self.total_cost, 2),
            "slices_executed": len([s for s in self.slice_schedule if s["status"] == "executed"]),
            "slices_total": self.num_slices,
            "elapsed_seconds": int(elapsed),
            "remaining_seconds": int(remaining_time),
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "paper_mode": self.paper_mode
        }
    
    async def execute_slice(self, current_price: float, slice_info: Dict) -> Dict:
        """Execute a single slice order"""
        quantity = slice_info["quantity"]
        
        # Simulate some slippage (0-0.05%)
        slippage_pct = random.uniform(0, 0.0005)
        if self.side == "buy":
            exec_price = current_price * (1 + slippage_pct)
        else:
            exec_price = current_price * (1 - slippage_pct)
        
        # Update totals
        slice_cost = quantity * exec_price
        self.total_cost += slice_cost if self.side == "buy" else -slice_cost
        self.executed_quantity += quantity
        self.remaining_quantity -= quantity
        
        # Update average price
        if self.executed_quantity > 0:
            self.avg_execution_price = abs(self.total_cost) / self.executed_quantity
        
        # Record execution
        execution = {
            "slice_index": slice_info["slice_index"],
            "timestamp": datetime.now().isoformat(),
            "side": self.side,
            "quantity": quantity,
            "price": round(exec_price, 4),
            "cost": round(slice_cost, 2),
            "cumulative_qty": self.executed_quantity,
            "avg_price": round(self.avg_execution_price, 4),
            "paper_mode": self.paper_mode
        }
        
        self.executed_slices.append(execution)
        slice_info["status"] = "executed"
        slice_info["execution"] = execution
        
        return execution
    
    async def tick(self, current_price: float) -> Optional[Dict]:
        """
        Process one tick of the TWAP executor
        Check if any slices are due for execution
        """
        if not self.is_running or self.is_paused or not self.start_time:
            return None
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        # Check if execution is complete
        if elapsed >= self.duration_minutes * 60 or self.remaining_quantity <= 0:
            self.is_running = False
            return {"status": "complete", "progress": self.get_progress()}
        
        # Find next pending slice that's due
        for slice_info in self.slice_schedule:
            if slice_info["status"] == "pending":
                if elapsed >= slice_info["scheduled_seconds"]:
                    return await self.execute_slice(current_price, slice_info)
                break  # Only execute in order
        
        return None
    
    def get_schedule(self) -> List[Dict]:
        """Get the full slice schedule"""
        return self.slice_schedule


# Active TWAP executors
_active_twaps: Dict[str, TWAPExecutor] = {}


async def create_twap_order(
    ticker: str,
    side: str,
    quantity: int,
    duration_minutes: int = 60,
    num_slices: int = 10,
    paper_mode: bool = True
) -> Dict:
    """Create and start a TWAP order"""
    executor = TWAPExecutor(
        ticker=ticker,
        side=side,
        total_quantity=quantity,
        duration_minutes=duration_minutes,
        num_slices=num_slices,
        paper_mode=paper_mode
    )
    executor.start()
    
    order_id = f"{ticker}_{side}_{datetime.now().strftime('%H%M%S')}"
    _active_twaps[order_id] = executor
    
    return {
        "order_id": order_id,
        "status": "started",
        "schedule": executor.get_schedule(),
        "progress": executor.get_progress()
    }


async def get_twap_status(order_id: str) -> Optional[Dict]:
    """Get status of a TWAP order"""
    executor = _active_twaps.get(order_id)
    if executor:
        return {
            "order_id": order_id,
            "progress": executor.get_progress(),
            "schedule": executor.get_schedule(),
            "executions": executor.executed_slices
        }
    return None


async def twap_tick(order_id: str, current_price: float) -> Optional[Dict]:
    """Process one tick for a TWAP order"""
    executor = _active_twaps.get(order_id)
    if executor:
        return await executor.tick(current_price)
    return None


async def cancel_twap(order_id: str) -> Dict:
    """Cancel a TWAP order"""
    executor = _active_twaps.get(order_id)
    if executor:
        executor.cancel()
        return {"order_id": order_id, "status": "cancelled", "progress": executor.get_progress()}
    return {"order_id": order_id, "status": "not_found"}
