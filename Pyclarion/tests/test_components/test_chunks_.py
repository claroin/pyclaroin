from pyClarion.base import feature, chunk
from pyClarion.components.chunks_ import Chunk
from pyClarion.numdicts import NumDict

import unittest


class TestChunkMethods(unittest.TestCase):

    def test_bottom_up_returns_mean_weighted_max_dimensional_strength(self):

        ch = Chunk(
            features={
                feature(tag=1, val="a", lag=0), 
                feature(tag=1, val="b", lag=0), 
                feature(tag=2, val="a", lag=1), 
                feature(tag=2, val="b", lag=1)
            },
            weights={(1, 0): 0.2}
        )

        strengths = NumDict({
            feature(tag=1, val="a", lag=0): 0.2,
            feature(tag=1, val="b", lag=0): 0.6,
            feature(tag=2, val="a", lag=1): 0.5,
            feature(tag=2, val="b", lag=1): 0.4
        })

        self.assertAlmostEqual(
            ch.bottom_up(strengths),
            (.2 * .6 + 1. * .5) / (.2 + 1.)
        )

    def test_top_down_returns_weighted_strengths(self):

        features = {
            feature(tag=1, val="a", lag=0), 
            feature(tag=1, val="b", lag=0), 
            feature(tag=2, val="a", lag=1), 
            feature(tag=2, val="b", lag=1)
        }

        ch = Chunk(
            features=features,
            weights={(1, 0): 0.2}
        )

        top_down = ch.top_down(.8)
        for f in features:
            with self.subTest(f=f, w=ch.weights[f.dim]):
                self.assertAlmostEqual(top_down[f], .8 * ch.weights[f.dim])


if __name__ == "__main__":
    unittest.main()
