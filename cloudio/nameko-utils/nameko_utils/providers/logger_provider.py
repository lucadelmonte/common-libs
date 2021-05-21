import logging
import json
from datetime import datetime
import traceback
import json_logging
from json_logging import JSONLogFormatter, JSONLogWebFormatter, \
                         JSONRequestLogFormatter, util
from nameko.extensions import DependencyProvider
from functools import wraps
import warnings

EMPTY_VALUE = '-'
COMPONENT_ID = EMPTY_VALUE
COMPONENT_NAME = EMPTY_VALUE
COMPONENT_INSTANCE_INDEX = 0


def _exception_info_to_dict(exc_info):
    exc_type, msg, traceback = exc_info
    info = {
        'type': str(exc_type),
        'message': str(msg),
        'traceback': str(traceback)
    }
    return {'exception_info': info}


def _build_extra(worker_ctx, result=None):

    mservice = {
        'name': worker_ctx.service_name,
        'method': worker_ctx.entrypoint.method_name,
        'args': str(worker_ctx.args),
        'kwargs': str(worker_ctx.kwargs)
    }

    if result:
        mservice['result'] = str(result)

    return {
        'props': {
            'correlation_id': worker_ctx.data.get('correlation_id', ''),
            'mservice': mservice,
            'disco_client_id': worker_ctx.data.get('disco_client_id', ''),
            'vhost_domain_suffix': worker_ctx.data.get('vhost_domain_suffix', ''),
            'app_name': worker_ctx.data.get('app_name', '')
        }
    }


def _build_message(message):
    return {'message': message}


def _build_msg(record):
    record_message = record.getMessage()

    if not isinstance(record_message, str):
        return record_message

    if record_message.startswith("{"):
        return json.loads(record_message)

    return _build_message(record_message)


def _method_logging(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger, msg, params = func(*args, **kwargs)
        logger(msg, **params)
    return wrapper


def _json_serialize(json_object, ensure_ascii=False):
    return json.dumps(json_object, ensure_ascii=ensure_ascii, sort_keys=True)


def _common_format(format):
    @wraps(format)
    def wrapper(instance, record):
        json_log_object = format(instance, record)

        if hasattr(record, 'props'):
            json_log_object.update(record.props)

        if record.exc_info or record.exc_text:
            json_log_object.update(instance.get_exc_fields(record))

        return _json_serialize(json_log_object)
    return wrapper


class LoggerProvider(DependencyProvider):
    """Logs exceptions and provides logger with worker's contextual info."""

    def __init__(self, logger_name):
        """:param logger_name: name of logger instance."""
        self.logger = logging.getLogger(logger_name)
        warnings.simplefilter('always', DeprecationWarning)
        logging.captureWarnings(True)

    def get_dependency(self, worker_ctx):
        """Create logger adapter with worker's contextual data."""
        return logging.LoggerAdapter(
            self.logger,
            extra=_build_extra(worker_ctx)
        )

    @_method_logging
    def worker_setup(self, worker_ctx):
        """Log task info, before starting task execution."""
        msg = "function {}() started".format(worker_ctx.entrypoint.method_name)
        params = {'extra': _build_extra(worker_ctx)}
        logger = self.logger.debug
        return (logger, msg, params)

    @_method_logging
    def worker_result(self, worker_ctx, result=None, exc_info=None):
        """Log exception info, if it is present."""
        params = {'extra': _build_extra(worker_ctx, result)}

        if exc_info:
            logger = self.logger.error
            msg = _exception_info_to_dict(exc_info)
        else:
            logger = self.logger.info
            msg = _build_message("function {}() finished".format(worker_ctx.entrypoint.method_name))

        return (logger, json.dumps(msg), params)


class NamekoLogFormatter(JSONLogFormatter):

    @_common_format
    def format(self, record):
        utcnow = datetime.utcnow()
        return {
            "type": "log",
            "written_at": util.iso_time_format(utcnow),
            "written_ts": util.epoch_nano_second(utcnow),
            "component_id": COMPONENT_ID,
            "component_name": COMPONENT_NAME,
            "component_instance": COMPONENT_INSTANCE_INDEX,
            "logger": record.name,
            "thread": record.threadName,
            "level": record.levelname,
            "line_no": record.lineno,
            "module": record.module,
            "msg": _build_msg(record)
        }


class FlaskLogFormatter(JSONLogWebFormatter):

    @_common_format
    def format(self, record):
        utcnow = datetime.utcnow()
        return {
            "type": "log",
            "written_at": util.iso_time_format(utcnow),
            "written_ts": util.epoch_nano_second(utcnow),
            "component_id": COMPONENT_ID,
            "component_name": COMPONENT_NAME,
            "component_instance": COMPONENT_INSTANCE_INDEX,
            "logger": record.name,
            "thread": record.threadName,
            "level": record.levelname,
            "module": record.module,
            "line_no": record.lineno,
            "correlation_id": _request_util.get_correlation_id(),
            "msg": _build_msg(record)
        }
