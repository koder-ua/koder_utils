from __future__ import annotations

import abc
import itertools
import re
from typing import Optional, Tuple, cast, List, Dict, Union, Iterator, Iterable

try:
    import numpy
except ImportError:
    numpy = None

from .inumeric import NumVector


class DataStorageTags:
    node_id = r'\d+.\d+.\d+.\d+:\d+'
    job_id = r'[-a-zA-Z0-9_]+_\d+'
    suite_id = r'[a-z_]+_\d+'
    sensor = r'[-a-z_]+'
    dev = r'[-a-zA-Z0-9_]+'
    metric = r'[-a-z_]+'
    tag = r'[a-z_.]+'


SensorIDS = Iterable[Dict[str, str]]
array1d = NumVector
array2d = NumVector

FieldsDct = Dict[str, Union[str, List[str]]]
DataStorageTagsDct = {name: f"(?P<{name}>{rr})"
                      for name, rr in DataStorageTags.__dict__.items()
                      if not name.startswith("__")}


class DataSource:
    def __init__(self, suite_id: str = None, job_id: str = None, node_id: str = None,
                 sensor: str = None, dev: str = None, metric: str = None, tag: str = None) -> None:
        self.suite_id = suite_id
        self.job_id = job_id
        self.node_id = node_id
        self.sensor = sensor
        self.dev = dev
        self.metric = metric
        self.tag = tag

    @property
    def metric_fqdn(self) -> str:
        return f"{self.sensor}.{self.dev}.{self.metric}"

    def verify(self):
        for attr_name, attr_val in self.__dict__.items():
            if '__' not in attr_name and attr_val is not None:
                assert re.match(getattr(DataStorageTags, attr_name) + "$", attr_val), \
                    f"Wrong field in DataSource - {attr_name}=={attr_val!r}"

    def __call__(self, **kwargs) -> DataSource:
        dct = self.__dict__.copy()
        dct.update(kwargs)
        return self.__class__(**dct)

    def __str__(self) -> str:
        return (f"suite={self.suite_id},job={self.job_id},node={self.node_id}," +
                f"path={self.sensor}.{self.dev}.{self.metric},tag={self.tag}")

    def __repr__(self) -> str:
        return str(self)

    @property
    def tpl(self) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str],
                           Optional[str], Optional[str], Optional[str]]:
        return self.suite_id, self.job_id, self.node_id, self.sensor, self.dev, self.metric, self.tag

    def __eq__(self, o: object) -> bool:
        return self.tpl == cast(DataSource, o).tpl

    def __hash__(self) -> int:
        return hash(self.tpl)


class PathSelector:
    def __init__(self) -> None:
        self.extra_mappings: Dict[str, Dict[str, List[FieldsDct]]] = {}
        # new_field_name:
        #     new_field_value:
        #         - {old_field1: old_value1(s), ...}
        #         - {old_field2: old_value2(s), ...}
        #         ....

    def add_mapping(self, param: str, val: str, **fields: Union[str, List[str]]) -> None:
        self.extra_mappings.setdefault(param, {}).setdefault(val, []).append(fields)

    def __call__(self, **mapping: Union[str, List[str]]) -> Iterator[Dict[str, str]]:
        # final cache may be created: mapping => result
        if not mapping:
            yield {}
        else:
            to_lst = lambda x: x if isinstance(x, list) else [x]
            extra: Dict[str, List[str]] = {}
            mapping_lst = {key: to_lst(val) for key, val in mapping.items()}
            cleared_mapping = mapping_lst.copy()
            for name, vals in mapping_lst.items():
                if name in self.extra_mappings:
                    extra[name] = to_lst(cleared_mapping.pop(name))

            if not extra:
                assert cleared_mapping == mapping_lst
                keys, vals = zip(*mapping_lst.items())
                for combination in itertools.product(*vals):
                    yield dict(zip(keys, combination))
            else:
                for extra_name, extra_vals in extra.items():
                    for extra_val in extra_vals:
                        for pdict in self.extra_mappings[extra_name][extra_val]:
                            params: Dict[str, List[str]] = cleared_mapping.copy()
                            for pkey, pval in pdict.items():
                                assert pkey not in params
                                params[pkey] = pval
                            yield from self(**params)


class IImagesStorage(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def check_plot_file(self, source: DataSource) -> Optional[str]:
        pass

    @abc.abstractmethod
    def put_plot_file(self, data: bytes, source: DataSource) -> str:
        pass
