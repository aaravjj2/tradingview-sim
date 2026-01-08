"""
Confidence Calibration Helper for VolGate Model

This script helps calibrate the confidence scores from the model
to better match realized outcome probabilities.

Usage:
    python calibrate_confidence.py --historical-data path/to/data.csv
"""

import json
import argparse
from typing import List, Dict, Tuple
import numpy as np


def calibration_curve(
    predictions: List[Dict],
    outcomes: List[int],
    n_bins: int = 10
) -> Tuple[List[float], List[float]]:
    """
    Compute calibration curve for confidence scores.
    
    Args:
        predictions: List of prediction dicts with 'confidence' key
        outcomes: List of binary outcomes (0 or 1)
        n_bins: Number of calibration bins
        
    Returns:
        (mean_predicted_prob, mean_actual_prob) for each bin
    """
    if len(predictions) != len(outcomes):
        raise ValueError("predictions and outcomes must have same length")
    
    confidences = [p.get('confidence', 0.5) for p in predictions]
    signals = [p.get('signal', 0) for p in predictions]
    
    # For calibration, we compare predicted probability of positive outcome
    # to actual positive outcome rate
    pred_probs = []
    for conf, sig in zip(confidences, signals):
        if sig == 1:
            pred_probs.append(conf)
        else:
            pred_probs.append(1 - conf)  # Probability of being correct about "no signal"
    
    bins = np.linspace(0, 1, n_bins + 1)
    bin_centers = (bins[:-1] + bins[1:]) / 2
    
    mean_predicted = []
    mean_actual = []
    
    for i in range(n_bins):
        mask = (np.array(pred_probs) >= bins[i]) & (np.array(pred_probs) < bins[i + 1])
        if np.sum(mask) > 0:
            mean_predicted.append(np.mean(np.array(pred_probs)[mask]))
            # For calibration, outcome should match signal direction
            actual_outcomes = [o == s for o, s in zip(
                np.array(outcomes)[mask], 
                np.array(signals)[mask]
            )]
            mean_actual.append(np.mean(actual_outcomes))
        else:
            mean_predicted.append(bin_centers[i])
            mean_actual.append(bin_centers[i])
    
    return mean_predicted, mean_actual


def compute_ece(predictions: List[Dict], outcomes: List[int], n_bins: int = 10) -> float:
    """
    Compute Expected Calibration Error (ECE).
    
    Lower is better. ECE of 0 means perfectly calibrated.
    """
    mean_pred, mean_actual = calibration_curve(predictions, outcomes, n_bins)
    
    # Weight by bin size (simplified - assumes equal bin counts)
    ece = np.mean(np.abs(np.array(mean_pred) - np.array(mean_actual)))
    
    return float(ece)


def isotonic_calibration(train_probs: List[float], train_outcomes: List[int]):
    """
    Fit isotonic regression for calibration.
    
    Returns a function that maps uncalibrated probabilities to calibrated ones.
    """
    from sklearn.isotonic import IsotonicRegression
    
    ir = IsotonicRegression(out_of_bounds='clip')
    ir.fit(train_probs, train_outcomes)
    
    return ir.predict


def main():
    parser = argparse.ArgumentParser(description='Calibrate VolGate confidence scores')
    parser.add_argument('--historical-data', type=str, help='Path to historical predictions CSV')
    parser.add_argument('--output', type=str, default='calibration_params.json', help='Output file')
    args = parser.parse_args()
    
    print("Confidence Calibration Helper")
    print("="*50)
    
    if not args.historical_data:
        print("No historical data provided. Using synthetic example.")
        
        # Generate synthetic example
        np.random.seed(42)
        n_samples = 100
        
        predictions = [
            {"signal": np.random.choice([0, 1]), "confidence": np.random.uniform(0.4, 0.9)}
            for _ in range(n_samples)
        ]
        
        # Simulate outcomes with some noise
        outcomes = []
        for p in predictions:
            # True outcome is correlated with signal and confidence
            base_prob = 0.5 + (p['confidence'] - 0.5) * 0.7
            if p['signal'] == 1:
                outcomes.append(1 if np.random.random() < base_prob else 0)
            else:
                outcomes.append(0 if np.random.random() < base_prob else 1)
        
        ece = compute_ece(predictions, outcomes)
        print(f"Expected Calibration Error (ECE): {ece:.4f}")
        
        mean_pred, mean_actual = calibration_curve(predictions, outcomes)
        print("\nCalibration Curve:")
        for mp, ma in zip(mean_pred, mean_actual):
            print(f"  Predicted: {mp:.2f} -> Actual: {ma:.2f}")
        
        # Save calibration summary
        calibration_data = {
            "ece": ece,
            "n_samples": n_samples,
            "calibration_curve": {
                "mean_predicted": [float(x) for x in mean_pred],
                "mean_actual": [float(x) for x in mean_actual]
            }
        }
        
        with open(args.output, 'w') as f:
            json.dump(calibration_data, f, indent=2)
        
        print(f"\nCalibration data saved to {args.output}")
    else:
        print(f"Loading historical data from {args.historical_data}")
        # TODO: Implement actual data loading
        print("Feature not yet implemented for real data.")


if __name__ == "__main__":
    main()
