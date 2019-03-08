from unittest.mock import Mock

from owca import platforms
from owca.platforms import RDTInformation

platform_mock = Mock(
    spec=platforms.Platform,
    sockets=1,
    rdt_information=RDTInformation(
        cbm_mask='fffff',
        min_cbm_bits='1',
        rdt_mb_control_enabled=False,
        num_closids=2,
        mb_bandwidth_gran=None,
        mb_min_bandwidth=None,
    ))