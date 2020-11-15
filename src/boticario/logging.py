from django.utils import timezone
from json_log_formatter import JSONFormatter


class BoticarioJSONFormatter(JSONFormatter):
    def add_record_field(self, extra, record, fieldname,
                         destination_name=None):
        if extra is None:
            return
        if not record:
            return
        if not destination_name:
            destination_name = fieldname
        value = getattr(record, fieldname, None)
        if value:
            extra[destination_name] = value

    def json_record(self, message, extra, record):
        extra['message'] = message
        if 'time' not in extra:
            extra['time'] = timezone.now()
        if record:
            self.add_record_field(extra, record, 'levelname',
                                  destination_name='level')
            self.add_record_field(extra, record, 'filename')
            self.add_record_field(extra, record, 'lineno')
            self.add_record_field(extra, record, 'request_id')
        if 'request' in extra:
            del extra['request']  # Nao e serializavel
        return extra
