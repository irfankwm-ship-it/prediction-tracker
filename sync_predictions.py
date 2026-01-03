#!/usr/bin/env python3
"""
Sync Predictions to Public Tracker

Exports predictions from the pipeline database to the public JSON file
for the prediction tracker website.

Usage:
    python sync_predictions.py                  # Sync all predictions
    python sync_predictions.py --add            # Interactive add new prediction
    python sync_predictions.py --evaluate ID    # Mark prediction outcome
"""

import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import uuid


class PredictionSync:
    def __init__(self):
        self.public_dir = Path("/home/irfan/canadian_intel_hub/public")
        self.json_path = self.public_dir / "predictions.json"
        self.predictions = self._load_predictions()

    def _load_predictions(self) -> list:
        """Load existing predictions from JSON."""
        if self.json_path.exists():
            with open(self.json_path, 'r') as f:
                return json.load(f)
        return []

    def _save_predictions(self):
        """Save predictions to JSON."""
        with open(self.json_path, 'w') as f:
            json.dump(self.predictions, f, indent=4)
        print(f"Saved {len(self.predictions)} predictions to {self.json_path}")

    def _generate_id(self) -> str:
        """Generate a unique prediction ID."""
        year = datetime.now().year
        count = len([p for p in self.predictions if p['id'].startswith(f'PRED-{year}')]) + 1
        return f"PRED-{year}-{count:03d}"

    def add_prediction(
        self,
        prediction: str,
        domain: str,
        confidence: int,
        due_days: int,
        verification: str,
        falsification: str,
        sources: list = None
    ) -> str:
        """Add a new prediction."""
        pred_id = self._generate_id()
        created = datetime.now().strftime("%Y-%m-%d")
        due = (datetime.now() + timedelta(days=due_days)).strftime("%Y-%m-%d")

        new_pred = {
            "id": pred_id,
            "prediction": prediction,
            "domain": domain,
            "confidence": confidence,
            "created_date": created,
            "due_date": due,
            "verification": verification,
            "falsification": falsification,
            "sources": sources or [],
            "outcome": "pending",
            "evaluated_date": None,
            "outcome_notes": None
        }

        self.predictions.append(new_pred)
        self._save_predictions()

        print(f"\nAdded prediction: {pred_id}")
        print(f"  Domain: {domain}")
        print(f"  Confidence: {confidence}%")
        print(f"  Due: {due}")

        return pred_id

    def evaluate_prediction(self, pred_id: str, outcome: str, notes: str = None):
        """Mark a prediction as correct or incorrect."""
        for pred in self.predictions:
            if pred['id'] == pred_id:
                pred['outcome'] = outcome
                pred['evaluated_date'] = datetime.now().strftime("%Y-%m-%d")
                pred['outcome_notes'] = notes
                self._save_predictions()

                print(f"\nEvaluated {pred_id}: {outcome.upper()}")
                if notes:
                    print(f"  Notes: {notes}")
                return True

        print(f"Prediction {pred_id} not found")
        return False

    def list_pending(self):
        """List all pending predictions."""
        pending = [p for p in self.predictions if p['outcome'] == 'pending']
        pending.sort(key=lambda x: x['due_date'])

        print(f"\n{'='*60}")
        print(f"PENDING PREDICTIONS ({len(pending)})")
        print('='*60)

        for p in pending:
            due = datetime.strptime(p['due_date'], "%Y-%m-%d")
            days_left = (due - datetime.now()).days

            status = ""
            if days_left < 0:
                status = " [OVERDUE]"
            elif days_left == 0:
                status = " [DUE TODAY]"
            elif days_left <= 2:
                status = f" [DUE IN {days_left}d]"

            print(f"\n{p['id']}{status}")
            print(f"  {p['prediction'][:80]}...")
            print(f"  Domain: {p['domain']} | Confidence: {p['confidence']}% | Due: {p['due_date']}")

    def show_stats(self):
        """Show prediction statistics."""
        total = len(self.predictions)
        evaluated = [p for p in self.predictions if p['outcome'] != 'pending']
        correct = [p for p in self.predictions if p['outcome'] == 'correct']
        incorrect = [p for p in self.predictions if p['outcome'] == 'incorrect']
        pending = [p for p in self.predictions if p['outcome'] == 'pending']

        accuracy = (len(correct) / len(evaluated) * 100) if evaluated else 0

        # Brier score
        brier = 0
        if evaluated:
            for p in evaluated:
                outcome_val = 1 if p['outcome'] == 'correct' else 0
                conf = p['confidence'] / 100
                brier += (conf - outcome_val) ** 2
            brier = brier / len(evaluated)

        print(f"\n{'='*60}")
        print("PREDICTION STATISTICS")
        print('='*60)
        print(f"  Total predictions:  {total}")
        print(f"  Evaluated:          {len(evaluated)}")
        print(f"  Correct:            {len(correct)}")
        print(f"  Incorrect:          {len(incorrect)}")
        print(f"  Pending:            {len(pending)}")
        print(f"  Accuracy:           {accuracy:.1f}%")
        print(f"  Brier Score:        {brier:.3f}")
        print('='*60)


def interactive_add(sync: PredictionSync):
    """Interactive mode to add a prediction."""
    print("\n" + "="*60)
    print("ADD NEW PREDICTION")
    print("="*60)

    prediction = input("\nPrediction statement:\n> ").strip()
    if not prediction:
        print("Cancelled.")
        return

    domain = input("\nDomain (Diplomacy/Security/Economic/Political/Canada):\n> ").strip()

    confidence = int(input("\nConfidence (50-95):\n> ").strip())

    due_days = int(input("\nDays until due (e.g., 5):\n> ").strip())

    verification = input("\nVerification criteria (how to prove correct):\n> ").strip()

    falsification = input("\nFalsification criteria (how to prove incorrect):\n> ").strip()

    sources_raw = input("\nSources (comma-separated, or blank):\n> ").strip()
    sources = [s.strip() for s in sources_raw.split(",")] if sources_raw else []

    print("\n" + "-"*60)
    print("REVIEW:")
    print(f"  Prediction: {prediction[:60]}...")
    print(f"  Domain: {domain}")
    print(f"  Confidence: {confidence}%")
    print(f"  Due in: {due_days} days")
    print("-"*60)

    confirm = input("\nConfirm? (y/n): ").strip().lower()
    if confirm == 'y':
        sync.add_prediction(
            prediction=prediction,
            domain=domain,
            confidence=confidence,
            due_days=due_days,
            verification=verification,
            falsification=falsification,
            sources=sources
        )
    else:
        print("Cancelled.")


def interactive_evaluate(sync: PredictionSync, pred_id: str):
    """Interactive mode to evaluate a prediction."""
    # Find prediction
    pred = next((p for p in sync.predictions if p['id'] == pred_id), None)
    if not pred:
        print(f"Prediction {pred_id} not found.")
        return

    print("\n" + "="*60)
    print(f"EVALUATE: {pred_id}")
    print("="*60)
    print(f"\n{pred['prediction']}")
    print(f"\nDomain: {pred['domain']} | Confidence: {pred['confidence']}%")
    print(f"Due: {pred['due_date']}")
    print(f"\nVerification: {pred['verification']}")
    print(f"Falsification: {pred['falsification']}")

    outcome = input("\nOutcome (correct/incorrect): ").strip().lower()
    if outcome not in ['correct', 'incorrect']:
        print("Invalid outcome. Use 'correct' or 'incorrect'.")
        return

    notes = input("Notes (what happened):\n> ").strip()

    sync.evaluate_prediction(pred_id, outcome, notes)


def main():
    parser = argparse.ArgumentParser(description="Prediction Tracker Sync")
    parser.add_argument("--add", action="store_true", help="Add new prediction")
    parser.add_argument("--evaluate", type=str, help="Evaluate prediction by ID")
    parser.add_argument("--pending", action="store_true", help="List pending predictions")
    parser.add_argument("--stats", action="store_true", help="Show statistics")

    args = parser.parse_args()

    sync = PredictionSync()

    if args.add:
        interactive_add(sync)
    elif args.evaluate:
        interactive_evaluate(sync, args.evaluate)
    elif args.pending:
        sync.list_pending()
    elif args.stats:
        sync.show_stats()
    else:
        # Default: show stats and pending
        sync.show_stats()
        sync.list_pending()


if __name__ == "__main__":
    main()
