# Copyright (c) Facebook, Inc. and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# pyre-unsafe

import re
from operator import attrgetter
from unittest import TestCase

import pandas as pd
import statsmodels
from kats.detectors.trend_mk import MKDetector
from kats.tests.detectors.utils import gen_no_trend_data_ndim, gen_trend_data_ndim
from parameterized.parameterized import parameterized

statsmodels_ver = float(
    re.findall("([0-9]+\\.[0-9]+)\\..*", statsmodels.__version__)[0]
)


class UnivariateMKDetectorTest(TestCase):
    def setUp(self) -> None:
        self.window_size = 20
        self.time = pd.Series(
            pd.date_range(start="2020-01-01", end="2020-06-20", freq="1D")
        )
        no_trend_data = gen_no_trend_data_ndim(time=self.time)
        trend_data, self.t_change = gen_trend_data_ndim(time=self.time)
        trend_seas_data, self.t_change_seas = gen_trend_data_ndim(
            time=self.time, seasonality=0.07
        )

        # no trend data
        self.d_no_trend = MKDetector(data=no_trend_data)
        self.detected_time_points_no_trend = self.d_no_trend.detector(
            window_size=self.window_size
        )

        # trend data
        self.d_trend = MKDetector(data=trend_data)
        self.detected_time_points_trend = self.d_trend.detector(
            window_size=self.window_size
        )
        self.metadata_trend = self.detected_time_points_trend[0]
        results_trend = self.d_trend.get_MK_statistics()
        self.up_trend_detected_trend = self.d_trend.get_MK_results(
            results_trend, direction="up"
        )["ds"]
        self.down_trend_detected_trend = self.d_trend.get_MK_results(
            results_trend, direction="down"
        )["ds"]

        # trend data anchor point
        self.detected_time_points_trend2 = self.d_trend.detector(training_days=30)
        results_trend2 = self.d_trend.get_MK_statistics()
        self.up_trend_detected_trend2 = self.d_trend.get_MK_results(
            results_trend2, direction="up"
        )["ds"]
        self.down_trend_detected_trend2 = self.d_trend.get_MK_results(
            results_trend2, direction="down"
        )["ds"]

        # trend data with seasonality
        self.d_seas = MKDetector(data=trend_seas_data)
        self.detected_time_points_seas = self.d_seas.detector(freq="weekly")
        results_seas = self.d_seas.get_MK_statistics()
        self.up_trend_detected_seas = self.d_seas.get_MK_results(
            results_seas, direction="up"
        )["ds"]
        self.down_trend_detected_seas = self.d_seas.get_MK_results(
            results_seas, direction="down"
        )["ds"]

        # trend data with seasonality anchor point
        self.detected_time_points_seas2 = self.d_seas.detector(
            training_days=30, freq="weekly"
        )
        results_seas2 = self.d_seas.get_MK_statistics()
        self.up_trend_detected_seas2 = self.d_seas.get_MK_results(
            results_seas2, direction="up"
        )["ds"]
        self.down_trend_detected_seas2 = self.d_seas.get_MK_results(
            results_seas2, direction="down"
        )["ds"]

    # test for no trend data
    def test_no_trend_data(self) -> None:
        self.assertEqual(len(self.detected_time_points_no_trend), 0)

    # test for trend data
    def test_detector_type(self) -> None:
        self.assertIsInstance(self.d_trend, self.metadata_trend.detector_type)

    def test_tau(self) -> None:
        self.assertIsInstance(self.metadata_trend.Tau, float)

    def test_is_univariate(self) -> None:
        self.assertFalse(self.metadata_trend.is_multivariate)

    def test_incr_trend(self) -> None:
        self.assertEqual(self.metadata_trend.trend_direction, "increasing")

    @parameterized.expand([["up_trend_detected_trend"], ["up_trend_detected_seas"]])
    def test_upward_after_start(self, up_trend_detected) -> None:
        self.assertGreaterEqual(
            attrgetter(up_trend_detected)(self).iloc[0],
            self.time[0],
            msg=f"The first {self.window_size}-days upward trend was not detected after it starts.",
        )

    @parameterized.expand(
        [
            ["up_trend_detected_trend", "t_change"],
            ["up_trend_detected_seas", "t_change_seas"],
        ]
    )
    def test_upward_before_end(self, up_trend_detected, t_change) -> None:
        self.assertLessEqual(
            attrgetter(up_trend_detected)(self).iloc[-1],
            self.time[attrgetter(t_change)(self)[0] + self.window_size],
            msg=f"The last {self.window_size}-days upward trend was not detected before it ends.",
        )

    @parameterized.expand(
        [
            ["down_trend_detected_trend", "t_change"],
            ["down_trend_detected_seas", "t_change_seas"],
        ]
    )
    def test_downward_after_start(self, down_trend_detected, t_change) -> None:
        self.assertGreaterEqual(
            attrgetter(down_trend_detected)(self).iloc[0],
            self.time[attrgetter(t_change)(self)[0]],
            msg=f"The first {self.window_size}-days downward trend was not detected after it starts.",
        )

    @parameterized.expand(
        [
            ["down_trend_detected_trend"],
            ["down_trend_detected_trend2"],
            ["down_trend_detected_seas"],
            ["down_trend_detected_seas2"],
        ]
    )
    def test_downward_before_end(self, down_trend_detected) -> None:
        self.assertEqual(
            attrgetter(down_trend_detected)(self).iloc[-1],
            self.time[len(self.time) - 1],
            msg=f"The last {self.window_size}-days downward trend was not detected before it ends.",
        )

    @parameterized.expand(
        [
            ["d_no_trend", "detected_time_points_no_trend"],
            ["d_trend", "detected_time_points_trend"],
            ["d_trend", "detected_time_points_trend2"],
            ["d_seas", "detected_time_points_seas"],
            ["d_seas", "detected_time_points_seas2"],
        ]
    )
    def test_plot(self, detector, detected_time_points) -> None:
        attrgetter(detector)(self).plot(attrgetter(detected_time_points)(self))


class MultivariateMKDetectorTest(TestCase):
    def setUp(self) -> None:
        self.window_size = 20
        self.time = pd.Series(
            pd.date_range(start="2020-01-01", end="2020-06-20", freq="1D")
        )
        self.ndim = 5
        no_trend_data = gen_no_trend_data_ndim(time=self.time, ndim=self.ndim)
        trend_data, self.t_change = gen_trend_data_ndim(time=self.time, ndim=self.ndim)
        trend_seas_data, self.t_change_seas = gen_trend_data_ndim(
            time=self.time, seasonality=0.07, ndim=self.ndim
        )

        # no trend data
        self.d_no_trend = MKDetector(data=no_trend_data)
        self.detected_time_points_no_trend = self.d_no_trend.detector(
            window_size=self.window_size
        )

        # trend data
        self.d_trend = MKDetector(data=trend_data, multivariate=True)
        self.detected_time_points_trend = self.d_trend.detector()
        results_trend = self.d_trend.get_MK_statistics()
        self.up_trend_detected_trend = self.d_trend.get_MK_results(
            results_trend, direction="up"
        )["ds"]
        self.down_trend_detected_trend = self.d_trend.get_MK_results(
            results_trend, direction="down"
        )["ds"]

        # trend data with seasonality
        self.d_seas = MKDetector(data=trend_seas_data, multivariate=True)
        self.detected_time_points_seas = self.d_seas.detector(freq="weekly")
        results_seas = self.d_seas.get_MK_statistics()
        self.up_trend_detected_seas = self.d_seas.get_MK_results(
            results_seas, direction="up"
        )["ds"]
        self.down_trend_detected_seas = self.d_seas.get_MK_results(
            results_seas, direction="down"
        )["ds"]

    # test for no trend data
    def test_no_trend_data(self) -> None:
        self.assertEqual(len(self.detected_time_points_no_trend), 0)

    def test_heatmap(self) -> None:
        self.d_no_trend.plot_heat_map()

    @parameterized.expand([["up_trend_detected_trend"], ["up_trend_detected_seas"]])
    def test_upward_after_start(self, up_trend_detected) -> None:
        self.assertGreaterEqual(
            attrgetter(up_trend_detected)(self).iloc[0],
            self.time[0],
            msg=f"The first {self.window_size}-days upward trend was not detected after it starts.",
        )

    @parameterized.expand(
        [
            ["up_trend_detected_trend", "t_change"],
            ["up_trend_detected_seas", "t_change_seas"],
        ]
    )
    def test_upward_before_end(self, up_trend_detected, t_change) -> None:
        self.assertLessEqual(
            attrgetter(up_trend_detected)(self).iloc[-1],
            self.time[attrgetter(t_change)(self)[0] + self.window_size],
            msg=f"The last {self.window_size}-days upward trend was not detected before it ends.",
        )

    @parameterized.expand(
        [
            ["down_trend_detected_trend", "t_change"],
            ["down_trend_detected_seas", "t_change_seas"],
        ]
    )
    def test_downward_after_start(self, down_trend_detected, t_change) -> None:
        self.assertGreaterEqual(
            attrgetter(down_trend_detected)(self).iloc[0],
            self.time[attrgetter(t_change)(self)[0]],
            msg=f"The first {self.window_size}-days downward trend was not detected after it starts.",
        )

    @parameterized.expand([["down_trend_detected_trend"], ["down_trend_detected_seas"]])
    def test_downward_before_end(self, down_trend_detected) -> None:
        self.assertEqual(
            attrgetter(down_trend_detected)(self).iloc[-1],
            self.time[len(self.time) - 1],
            msg=f"The last {self.window_size}-days downward trend was not detected before it ends.",
        )

    @parameterized.expand(
        [
            ["d_no_trend", "detected_time_points_no_trend"],
            ["d_trend", "detected_time_points_trend"],
            ["d_seas", "detected_time_points_seas"],
        ]
    )
    def test_plot(self, detector, detected_time_points) -> None:
        attrgetter(detector)(self).plot(attrgetter(detected_time_points)(self))
