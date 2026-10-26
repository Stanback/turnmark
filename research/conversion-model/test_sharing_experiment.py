"""Checks for the experimental intervention, using invented swims only."""
import unittest

import numpy as np

import evaluate_and_train as e
from sharing_experiment import adjust, groups, predict, shared_curve, variant
from test_evaluate_and_train import known_pairs


class SharingExperimentTests(unittest.TestCase):
    def test_precision_intervention_and_endpoints(self):
        # Raw N(10, 4), prior N(2, 1): posterior N(3.6, .8).
        raw = (10., 4.)
        post = e.Posterior(3.6, .8, .2)
        self.assertEqual(adjust(raw, post, 1), post)
        self.assertEqual(adjust(raw, post, 0), e.Posterior(10., 4., 1.))
        pooled = adjust(raw, post, float('inf'))
        self.assertAlmostEqual(pooled.value, 2.)
        self.assertAlmostEqual(pooled.var, 1.)
        half = adjust(raw, post, .5)
        self.assertAlmostEqual(half.value, 14 / 3)
        self.assertAlmostEqual(half.var, 4 / 3)
        self.assertGreater(half.own_share, post.own_share)

    def test_baseline_reconstruction_and_vector_arithmetic(self):
        noise = {c: .015 for c in e.COURSES}
        pairs = known_pairs(100, noise)
        base = e.EquivalenceModel()
        base.fit(pairs, {(c, '100-FR'): v ** 2 for c, v in noise.items()})
        clone = variant(base, groups(pairs), 1, 1)
        self.assertEqual(base.tables, clone.tables)
        for level, slope in ((1, 1), (0, 0), (.25, 4), (float('inf'), float('inf'))):
            model = variant(base, groups(pairs), level, slope)
            self.assertTrue(np.array_equal(predict(model, pairs), [model.predict(p) for p in pairs]))
        self.assertEqual(base.tables, clone.tables, 'Experiment mutated baseline')
        pooled = shared_curve(base, groups(pairs))
        self.assertEqual(pooled.tables[('100-FR', 'women')], pooled.tables[('100-FR', 'men')])


if __name__ == '__main__':
    unittest.main()
