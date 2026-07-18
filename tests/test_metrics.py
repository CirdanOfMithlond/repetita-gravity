from __future__ import annotations

import unittest

from repetita.metrics import PassMetrics, decide_continuation, plan_complexity
from repetita.pipeline import analyse_document


class ComplexityTests(unittest.TestCase):
    def test_short_simple_document_plans_one_pass(self) -> None:
        result = analyse_document("# Note\n\nA concise unique statement remains here.")
        plan = plan_complexity(result)
        self.assertEqual(plan.planned_passes, 1)

    def test_recurrence_density_affects_plan_not_length_alone(self) -> None:
        unique = analyse_document("# Note\n\n" + "A unique statement. " * 2)
        repeated = analyse_document(
            "# One\n\nThe archive preserves every original record.\n\n"
            "# Two\n\nThe archive preserves every original record.\n\n"
            "# Three\n\nThe archive preserves every original record."
        )
        self.assertGreaterEqual(plan_complexity(repeated).complexity_index, plan_complexity(unique).complexity_index)


class ContinuationTests(unittest.TestCase):
    def metrics(self, **changes) -> PassMetrics:
        base = dict(
            pass_number=1,
            repetition_burden=0.2,
            substantive_ledger_coverage=1.0,
            thematic_dispersion=0.2,
            pass_instability=0.1,
            unresolved_occurrences=2,
            critical_failures=(),
        )
        base.update(changes)
        return PassMetrics(**base)

    def test_coverage_failure_stops_not_verified(self) -> None:
        decision = decide_continuation(self.metrics(substantive_ledger_coverage=0.99), initially_planned=3)
        self.assertEqual(decision.action, "STOP_NOT_VERIFIED")

    def test_stability_can_stop_before_initial_plan(self) -> None:
        previous = self.metrics(pass_number=1, repetition_burden=0.20)
        current = self.metrics(pass_number=2, repetition_burden=0.195, pass_instability=0.01)
        decision = decide_continuation(current, initially_planned=4, previous=previous)
        self.assertEqual(decision.action, "STOP_STABLE")
        self.assertEqual(decision.estimated_passes_remaining, 0)

    def test_unresolved_work_can_add_one_pass(self) -> None:
        decision = decide_continuation(self.metrics(pass_number=2), initially_planned=2)
        self.assertEqual(decision.action, "ADD_PASS")
        self.assertEqual(decision.passes_initially_planned, 3)

    def test_never_exceeds_five_passes(self) -> None:
        decision = decide_continuation(self.metrics(pass_number=5), initially_planned=5)
        self.assertEqual(decision.action, "STOP_SAFETY_CAP")

    def test_risk_over_benefit_stops_for_review(self) -> None:
        decision = decide_continuation(
            self.metrics(), initially_planned=3, conservation_risk=0.7, expected_benefit=0.4
        )
        self.assertEqual(decision.action, "STOP_HUMAN_REVIEW")


if __name__ == "__main__":
    unittest.main()

