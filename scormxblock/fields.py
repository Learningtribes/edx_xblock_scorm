# -*- coding: utf-8 -*-
from xblock.fields import DateTime as DefaultDateTime


class DateTime(DefaultDateTime):
    DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'

