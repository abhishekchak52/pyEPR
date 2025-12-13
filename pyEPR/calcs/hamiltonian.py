"""
Hamiltonian and Matrix Operations.
Hamiltonian operations heavily draw on qutip package.
This package must be installed for them to work.
"""

try:
    import qutip
    from qutip import Qobj  # basis, tensor,
except (ImportError, ModuleNotFoundError):
    Qobj = None
    pass

from ..toolbox.pythonic import fact


class MatrixOps(object):
    @staticmethod
    def cos(op_cos_arg: Qobj):
        """
        Make cosine operator matrix from argument  op_cos_arg

            op_cos_arg (qutip.Qobj) : argument of the cosine
        """

        return 0.5 * ((1j * op_cos_arg).expm() + (-1j * op_cos_arg).expm())

    @staticmethod
    def cos_approx(x, cos_trunc=5):
        """
        Compute the nonlinear part of the cosine potential for EPR analysis.
        
        The Taylor series for cos(x) is:
            cos(x) = 1 - x²/2! + x⁴/4! - x⁶/6! + ...
        
        This function returns: cos(x) - 1 + x²/2!
        which equals the series starting from the x⁴ term:
            = x⁴/4! - x⁶/6! + x⁸/8! - ...
        
        The constant and x² terms are intentionally omitted because:
        - The constant 1 shifts all energies equally (no physical effect)
        - The x² term is linear in photon number and is included in the linear Hamiltonian
        
        Uses expm() to compute cos(x) exactly, avoiding QuTiP/SciPy sparse matrix
        index compatibility issues that occur with direct matrix multiplication.
        
        Note: The cos_trunc parameter is kept for backward compatibility but is no longer
        used. The exact cosine is computed instead of a truncated Taylor series, which
        is more accurate and avoids numerical issues.
        
        Args:
            x: QuTiP Qobj representing the flux operator
            cos_trunc: (deprecated) Previously used to truncate Taylor series. Now ignored.
        """
        from functools import reduce
        import numpy as np
        
        # Convert to dense to avoid QuTiP v4.x / SciPy sparse matrix int32 index issues
        # The matrices are small (fock_trunc^n_modes), so dense is fine
        x_dense = x.full()
        dims = x.dims
        
        # Compute exact cos(x) using dense matrix exponential
        # cos(x) = (e^(ix) + e^(-ix)) / 2
        from scipy.linalg import expm
        cos_dense = 0.5 * (expm(1j * x_dense) + expm(-1j * x_dense))
        
        # Compute x²
        x2_dense = x_dense @ x_dense
        
        # Identity matrix
        identity_dense = np.eye(x_dense.shape[0], dtype=complex)
        
        # Result: cos(x) - 1 + x²/2
        result_dense = cos_dense - identity_dense + x2_dense / 2.0
        
        # Convert back to Qobj
        return qutip.Qobj(result_dense, dims=dims)

    @staticmethod
    def dot(ais, bis):
        """
        Dot product
        """
        return sum(ai * bi for ai, bi in zip(ais, bis))


def _safe_qobj_mult(a, b):
    """
    Safely multiply two Qobjs, avoiding QuTiP v4.x sparse matrix int32 index issues.
    Falls back to dense multiplication if sparse fails.
    """
    try:
        return a * b
    except TypeError:
        # Sparse matrix index issue - use dense multiplication
        import numpy as np
        result_dense = a.full() @ b.full()
        return qutip.Qobj(result_dense, dims=[a.dims[0], b.dims[1]])


def _safe_inner_product_norm(bra, ket):
    """
    Safely compute |<bra|ket>|, the absolute value of inner product.
    Handles QuTiP v4.x sparse matrix int32 index issues.
    Returns a float (not a Qobj).
    """
    try:
        result = bra.dag() * ket
        # For a 1x1 Qobj, norm() gives |<bra|ket>|
        return result.norm()
    except TypeError:
        # Sparse matrix index issue - use dense
        import numpy as np
        result = bra.dag().full() @ ket.full()
        return abs(complex(result[0, 0]))


class HamOps(object):
    @staticmethod
    def fock_state_on(d: dict, fock_trunc: int, N_modes: int):
        """d={mode number: # of photons} In the bare eigen basis"""
        # give me the value d[i]  or 0 if d[i] does not exist
        return qutip.tensor(
            *[qutip.basis(fock_trunc, d.get(i, 0)) for i in range(N_modes)]
        )

    @staticmethod
    def closest_state_to(s: Qobj, energyMHz, evecs):
        """
        Returns the energy of the closest state to s
        """

        def distance(s2):
            return _safe_inner_product_norm(s, s2[1])

        return max(zip(energyMHz, evecs), key=distance)

    @staticmethod
    def closest_state_to_idx(s: Qobj, evecs):
        """
        Returns the index
        """

        def distance(s2):
            return _safe_inner_product_norm(s, s2[1])

        return max(zip(range(len(evecs)), evecs), key=distance)

    @staticmethod
    def identify_Fock_levels(fock_trunc: int, evecs, N_modes=2, Fock_max=4):
        """
        Return quantum numbers in terms of the undiagonalized eigenbasis.
        """
        #  to do: need to turn Fock_max into arb algo on each mode

        def fock_state_on(d):
            return HamOps.fock_state_on(d, fock_trunc, N_modes)

        def closest_state_to_idx(s):
            return HamOps.closest_state_to_idx(s, evecs)

        FOCKr = {}
        for d1 in range(Fock_max):
            for d2 in range(Fock_max):
                d = {0: d1, 1: d2}
                FOCKr[closest_state_to_idx(fock_state_on(d))[0]] = d
        return FOCKr
