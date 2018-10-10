# Copyright (c) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


def check_cbm_bits(mask: str, cbm_mask: str, min_cbm_bits: str):
    mask = int(mask, 16)
    cbm_mask = int(cbm_mask, 16)
    if  mask > cbm_mask:
        raise ValueError('Mask is bigger than allowed')

    bin_mask = format(mask, 'b')
    number_of_cbm_bits = 0
    series_of_ones_finished = False
    previous = '0'

    for bit in bin_mask:
        if bit == '1':
            if series_of_ones_finished:
                raise ValueError('Bit series of ones in mask '
                                 'must occur without a gap between them')

            number_of_cbm_bits += 1
            previous = bit
        elif bit == '0':
            if previous == '1':
                series_of_ones_finished = True

            previous = bit

    min_cbm_bits = int(min_cbm_bits)
    if number_of_cbm_bits < min_cbm_bits:
        raise ValueError(str(number_of_cbm_bits) +
                         " cbm bits. Requires minimum " +
                         str(min_cbm_bits))
