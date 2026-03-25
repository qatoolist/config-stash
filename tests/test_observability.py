"""Tests for configuration observability and metrics."""

import time
import unittest
from unittest.mock import Mock, patch

from config_stash.config import Config
from config_stash.loaders import YamlLoader
from config_stash.observability import (
    ConfigAccessMetric,
    ConfigEventEmitter,
    ConfigMetrics,
    ConfigObserver,
)


class TestConfigAccessMetric(unittest.TestCase):
    """Test configuration access metrics."""

    def test_access_metric_initialization(self):
        """Test initializing access metric."""
        metric = ConfigAccessMetric(key="test_key")
        self.assertEqual(metric.key, "test_key")
        self.assertEqual(metric.access_count, 0)

    def test_access_metric_record_access(self):
        """Test recording access."""
        metric = ConfigAccessMetric(key="test_key")
        metric.record_access(access_time=0.001)
        self.assertEqual(metric.access_count, 1)
        self.assertIsNotNone(metric.first_access)
        self.assertIsNotNone(metric.last_access)
        self.assertEqual(metric.total_access_time, 0.001)

    def test_access_metric_multiple_accesses(self):
        """Test recording multiple accesses."""
        metric = ConfigAccessMetric(key="test_key")
        metric.record_access(0.001)
        metric.record_access(0.002)
        metric.record_access(0.003)

        self.assertEqual(metric.access_count, 3)
        self.assertEqual(metric.total_access_time, 0.006)
        self.assertAlmostEqual(metric.avg_access_time, 0.002, places=3)


class TestConfigMetrics(unittest.TestCase):
    """Test configuration metrics."""

    def test_metrics_initialization(self):
        """Test initializing metrics."""
        metrics = ConfigMetrics()
        self.assertEqual(metrics.total_keys, 0)
        self.assertEqual(metrics.reload_count, 0)
        self.assertEqual(metrics.change_count, 0)

    def test_metrics_record_reload(self):
        """Test recording reload."""
        metrics = ConfigMetrics()
        metrics.record_reload(0.1)
        self.assertEqual(metrics.reload_count, 1)
        self.assertIsNotNone(metrics.last_reload)
        self.assertEqual(len(metrics.reload_durations), 1)

    def test_metrics_record_change(self):
        """Test recording change."""
        metrics = ConfigMetrics()
        metrics.record_change()
        self.assertEqual(metrics.change_count, 1)
        self.assertIsNotNone(metrics.last_change)

    def test_metrics_record_access(self):
        """Test recording access."""
        metrics = ConfigMetrics()
        metrics.record_access("test_key", 0.001)
        self.assertIn("test_key", metrics.access_metrics)
        self.assertEqual(metrics.access_metrics["test_key"].access_count, 1)

    def test_metrics_get_statistics(self):
        """Test getting statistics."""
        metrics = ConfigMetrics()
        metrics.total_keys = 10
        metrics.record_access("key1", 0.001)
        metrics.record_access("key2", 0.002)
        metrics.record_reload(0.1)
        metrics.record_change()

        stats = metrics.get_statistics()
        self.assertEqual(stats["total_keys"], 10)
        self.assertEqual(stats["accessed_keys"], 2)
        self.assertEqual(stats["reload_count"], 1)
        self.assertEqual(stats["change_count"], 1)
        self.assertEqual(len(stats["top_accessed_keys"]), 2)


class TestConfigObserver(unittest.TestCase):
    """Test configuration observer."""

    def test_observer_initialization(self):
        """Test initializing observer."""
        observer = ConfigObserver()
        self.assertTrue(observer._enabled)

    def test_observer_enable_disable(self):
        """Test enabling/disabling observer."""
        observer = ConfigObserver()
        observer.disable()
        self.assertFalse(observer._enabled)
        observer.enable()
        self.assertTrue(observer._enabled)

    def test_observer_record_key_access(self):
        """Test recording key access."""
        observer = ConfigObserver()
        observer.record_key_access("test_key", 0.001)
        self.assertIn("test_key", observer.metrics.access_metrics)

    def test_observer_record_reload(self):
        """Test recording reload."""
        observer = ConfigObserver()
        observer.record_reload(0.1)
        self.assertEqual(observer.metrics.reload_count, 1)

    def test_observer_record_change(self):
        """Test recording change."""
        observer = ConfigObserver()
        observer.record_change()
        self.assertEqual(observer.metrics.change_count, 1)

    def test_observer_get_metrics(self):
        """Test getting metrics."""
        observer = ConfigObserver()
        observer.record_key_access("test_key")
        metrics = observer.get_metrics()
        self.assertIsInstance(metrics, ConfigMetrics)

    def test_observer_get_statistics(self):
        """Test getting statistics."""
        observer = ConfigObserver()
        observer.metrics.total_keys = 10
        observer.record_key_access("test_key", 0.001)
        stats = observer.get_statistics()
        self.assertIn("total_keys", stats)

    def test_observer_reset_metrics(self):
        """Test resetting metrics."""
        observer = ConfigObserver()
        observer.record_key_access("test_key")
        observer.reset_metrics()
        self.assertEqual(observer.metrics.change_count, 0)
        self.assertEqual(len(observer.metrics.access_metrics), 0)


class TestConfigEventEmitter(unittest.TestCase):
    """Test configuration event emitter."""

    def test_event_emitter_initialization(self):
        """Test initializing event emitter."""
        emitter = ConfigEventEmitter()
        self.assertEqual(len(emitter._listeners), 0)

    def test_event_emitter_on(self):
        """Test registering event listener."""
        emitter = ConfigEventEmitter()
        callback = Mock()

        emitter.on("test_event", callback)
        self.assertIn("test_event", emitter._listeners)
        self.assertIn(callback, emitter._listeners["test_event"])

    def test_event_emitter_emit(self):
        """Test emitting event."""
        emitter = ConfigEventEmitter()
        callback = Mock()

        emitter.on("test_event", callback)
        emitter.emit("test_event", "arg1", "arg2", key="value")

        callback.assert_called_once_with("arg1", "arg2", key="value")

    def test_event_emitter_off(self):
        """Test unregistering event listener."""
        emitter = ConfigEventEmitter()
        callback = Mock()

        emitter.on("test_event", callback)
        emitter.off("test_event", callback)

        emitter.emit("test_event")
        callback.assert_not_called()

    def test_event_emitter_multiple_listeners(self):
        """Test multiple listeners for same event."""
        emitter = ConfigEventEmitter()
        callback1 = Mock()
        callback2 = Mock()

        emitter.on("test_event", callback1)
        emitter.on("test_event", callback2)
        emitter.emit("test_event")

        callback1.assert_called_once()
        callback2.assert_called_once()


class TestConfigObservabilityIntegration(unittest.TestCase):
    """Test observability integration with Config."""

    def test_config_enable_observability(self):
        """Test enabling observability on Config."""
        config = Config(env="test", loaders=[], enable_ide_support=False)
        observer = config.enable_observability()
        self.assertIsNotNone(observer)
        self.assertIsInstance(observer, ConfigObserver)

    def test_config_enable_events(self):
        """Test enabling events on Config."""
        config = Config(env="test", loaders=[], enable_ide_support=False)
        emitter = config.enable_events()
        self.assertIsNotNone(emitter)
        self.assertIsInstance(emitter, ConfigEventEmitter)

    def test_config_get_metrics(self):
        """Test getting metrics from Config."""
        config = Config(env="test", loaders=[], enable_ide_support=False)
        observer = config.enable_observability()
        metrics = config.get_metrics()
        self.assertIsNotNone(metrics)
        self.assertIsInstance(metrics, dict)


if __name__ == "__main__":
    unittest.main()
