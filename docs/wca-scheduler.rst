=============
wca-scheduler
=============

.. contents:: Table of Contents

**This software is pre-production and should not be deployed to production servers.**

Introduction
============
wca-scheduler is special type of controller that assigns pods to nodes using algorithms provided by user. 

Configuration
=============
You can configure scheduler in following way in ``config.yaml``:  

.. code-block:: yaml

        loggers:
          scheduler.main: DEBUG
        algorithm: !NOPAlgorithm
          ...

Algorithms
==========
If you want to implement a new algorithm use interface below: 

.. code-block:: python

        #  https://github.com/kubernetes/kubernetes/blob/release-1.15/pkg/scheduler/api/types.go#L299
        @dataclass
        class ExtenderFilterResult():
            Nodes: Optional[List[Dict]] = None
            NodeNames: List[NodeName] = field(default_factory=lambda: [])
            FailedNodes: Dict[NodeName, FailureMessage] = field(default_factory=lambda: {})
            Error: str = ''

            def __post_init__(self):
                if self.Nodes:
                    raise UnsupportedCase()

                assure_type(self.NodeNames, List[NodeName])
                assure_type(self.FailedNodes, Dict[NodeName, FailureMessage])
                assure_type(self.Error, str)


        #  https://github.com/kubernetes/kubernetes/blob/release-1.15/pkg/scheduler/api/types.go#L331
        @dataclass
        class HostPriority():
            Host: str
            Score: int

            def __post_init__(self):
                assure_type(self.Host, str)
                assure_type(self.Score, int)


        #  https://github.com/kubernetes/kubernetes/blob/release-1.15/pkg/scheduler/api/types.go#L284
        @dataclass
        class ExtenderArgs:
            Nodes: Optional[List[Dict]]
            Pod: Dict
            NodeNames: List[NodeName]

            def __post_init__(self):

                if self.Nodes:
                    raise UnsupportedCase()

                assure_type(self.Pod, dict)
                assure_type(self.NodeNames, List[str])

        class Algorithm(ABC):
            @abstractmethod
            def filter(self, extender_args: ExtenderArgs) -> Tuple[ExtenderFilterResult, List[Metric]]:
                pass

            @abstractmethod
            def prioritize(self, extender_args: ExtenderArgs) -> Tuple[List[HostPriority], List[Metric]]:
                pass

            @abstractmethod
            def get_metrics_registry(self) -> Optional[MetricRegistry]:
                return None

            @abstractmethod
            def get_metrics_names(self) -> List[str]:
                return []

            @abstractmethod
            def reinit_metrics(self):
                pass

Register new component in ``wca/scheduler/components.py``.


Example deployment
==================
Check documentation of `example deployment <../examples/kubernetes/wca-scheduler/README.rst>`_
