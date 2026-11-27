"""Versioned prospective numeric patch. No monkey-patch or changes to frozen QV."""
from decimal import Decimal,localcontext
from functools import lru_cache
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
WS=ROOT.parents[2]
sys.path.insert(0,str(WS/'chapter4/mechanisms/vote_escrow_capping'))
from policies import WalletSqrt,InputError

PATCH_ID='QV_NUMERIC_TYPED_CACHE_V2'
@lru_cache(maxsize=100000,typed=True)
def _root_validated(value):
    with localcontext() as ctx:
        ctx.prec=100
        return value.sqrt()
def safe_root(value):
    # Validate outside cache so no equality/hash collision can bypass validation.
    if not isinstance(value,Decimal) or not value.is_finite() or value<0:
        raise InputError('V2 requires finite nonnegative Decimal source VP')
    return _root_validated(value)
class WalletSqrtNumericV2(WalletSqrt):
    implementation_version=PATCH_ID
    # Formula/weight units unchanged; implementation patch tracked separately.
    def weight(self,ballot,context=None):return safe_root(ballot.vp)
