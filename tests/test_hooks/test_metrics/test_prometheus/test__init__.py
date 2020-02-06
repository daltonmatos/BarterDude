import freezegun
from asynctest import TestCase, Mock, patch
from tests.helpers import get_app

from barterdude.hooks.metrics.prometheus import Prometheus
from barterdude.hooks.metrics.prometheus.definition import Definition


class TestPrometheus(TestCase):
    def setUp(self):
        self.app = get_app()
        self.registry = Mock()
        self.definition = Definition()
        self.mock_sender = Mock()
        self.definition.get_sender = Mock(return_value=self.mock_sender)
        self.labels = {"test": "my_test"}
        self.prometheus = Prometheus(
            barterdude=self.app,
            labels=self.labels,
            path="/metrics",
            registry=self.registry,
            definition=self.definition
        )

    @patch("barterdude.hooks.metrics.prometheus.generate_latest")
    async def test_should_call_response_from_prometheus(self, mock):
        mock.return_value = "test prometheus"
        response = await self.prometheus()
        mock.assert_called_once()
        mock.assert_called_with(self.registry)
        self.assertEqual(response.status, 200)
        self.assertEqual(
            response.content_type, "text/plain"
        )
        self.assertEqual(response.charset, "utf-8")
        self.assertEqual(
            response.body._value, bytes(mock.return_value, "utf-8")
        )

    async def test_should_call_prometheus_on_before_consume(self):
        mock_count = Mock()
        mock_count.inc = Mock()
        self.mock_sender.labels = Mock(
            return_value=mock_count
        )
        await self.prometheus.before_consume({})
        self.mock_sender.labels.assert_called_once()
        self.mock_sender.labels.assert_called_with(**self.labels)
        mock_count.inc.assert_called_once()

    async def test_should_call_prometheus_on_success(self):
        mock_sender = Mock()
        mock_sender.inc = Mock()
        mock_sender.observe = Mock()
        self.mock_sender.labels = Mock(
            return_value=mock_sender
        )
        await self.prometheus.before_consume({})
        await self.prometheus.on_success({})
        self.assertEqual(self.mock_sender.labels.call_count, 3)
        self.mock_sender.labels.assert_called_with(
            error=None, state='success', test='my_test'
        )
        self.assertEqual(mock_sender.inc.call_count, 2)
        mock_sender.observe.assert_called_once()

    async def test_should_call_prometheus_on_fail(self):
        mock_sender = Mock()
        mock_sender.inc = Mock()
        mock_sender.observe = Mock()
        self.mock_sender.labels = Mock(
            return_value=mock_sender
        )
        await self.prometheus.before_consume({})
        await self.prometheus.on_fail({}, Exception())
        self.assertEqual(self.mock_sender.labels.call_count, 3)
        self.mock_sender.labels.assert_called_with(
            error="<class 'Exception'>", state='fail', test='my_test'
        )
        self.assertEqual(mock_sender.inc.call_count, 2)
        mock_sender.observe.assert_called_once()

    async def test_should_measure_time_on_success(self):
        mock_sender = Mock()
        mock_sender.inc = Mock()
        mock_sender.observe = Mock()
        self.mock_sender.labels = Mock(
            return_value=mock_sender
        )
        with freezegun.freeze_time() as freeze:
            await self.prometheus.before_consume({})
            freeze.tick()
            await self.prometheus.on_success({})
        mock_sender.observe.assert_called_once()
        mock_sender.observe.assert_called_with(1.0)

    async def test_should_measure_time_on_fail(self):
        mock_sender = Mock()
        mock_sender.inc = Mock()
        mock_sender.observe = Mock()
        self.mock_sender.labels = Mock(
            return_value=mock_sender
        )
        with freezegun.freeze_time() as freeze:
            await self.prometheus.before_consume({})
            freeze.tick()
            await self.prometheus.on_fail({}, Exception())
        mock_sender.observe.assert_called_once()
        mock_sender.observe.assert_called_with(1.0)
