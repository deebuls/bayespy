################################################################################
# Copyright (C) 2011-2012,2014 Jaakko Luttinen
#
# This file is licensed under the MIT License.
################################################################################


"""
Module for the Dirichlet distribution node.
"""

import numpy as np
import scipy.special as special

from bayespy.utils import random

from .expfamily import ExponentialFamily, ExponentialFamilyDistribution
from .constant import Constant
from .node import Node, Moments, ensureparents


class DirichletPriorMoments(Moments):
    """
    Class for the moments of Dirichlet conjugate-prior variables.
    """


    def __init__(self, categories):
        self.categories = categories
        self.dims = ( (categories,), () )
        return


    def compute_fixed_moments(self, alpha):
        """
        Compute the moments for a fixed value
        """

        alpha = np.asanyarray(alpha)
        if np.ndim(alpha) < 1:
            raise ValueError("The prior sample sizes must be a vector")
        if np.any(alpha < 0):
            raise ValueError("The prior sample sizes must be non-negative")

        gammaln_sum = special.gammaln(np.sum(alpha, axis=-1))
        sum_gammaln = np.sum(special.gammaln(alpha), axis=-1)
        z = gammaln_sum - sum_gammaln
        return [alpha, z]


    @classmethod
    def from_values(cls, alpha):
        """
        Return the shape of the moments for a fixed value.
        """
        if np.ndim(alpha) < 1:
            raise ValueError("The array must be at least 1-dimensional array.")
        categories = np.shape(alpha)[-1]
        return cls(categories)


class DirichletMoments(Moments):
    """
    Class for the moments of Dirichlet variables.
    """


    def __init__(self, categories):
        self.categories = categories
        self.dims = ( (categories,), )


    def compute_fixed_moments(self, p):
        """
        Compute the moments for a fixed value
        """
        # Check that probabilities are non-negative
        p = np.asanyarray(p)
        if np.ndim(p) < 1:
            raise ValueError("Probabilities must be given as a vector")
        if np.any(p < 0) or np.any(p > 1):
            raise ValueError("Probabilities must be in range [0,1]")
        if not np.allclose(np.sum(p, axis=-1), 1.0):
            raise ValueError("Probabilities must sum to one")
        # Normalize probabilities
        p = p / np.sum(p, axis=-1, keepdims=True)
        # Message is log-probabilities
        logp = np.log(p)
        u = [logp]
        return u


    @classmethod
    def from_values(cls, x):
        """
        Return the shape of the moments for a fixed value.
        """
        if np.ndim(x) < 1:
            raise ValueError("Probabilities must be given as a vector")
        categories = np.shape(x)[-1]
        return cls(categories)


class DirichletDistribution(ExponentialFamilyDistribution):
    """
    Class for the VMP formulas of Dirichlet variables.
    """

    
    def compute_message_to_parent(self, parent, index, u_self, u_alpha):
        r"""
        Compute the message to a parent node.
        """
        raise NotImplementedError()

    
    def compute_phi_from_parents(self, u_alpha, mask=True):
        r"""
        Compute the natural parameter vector given parent moments.
        """
        return [u_alpha[0]]

    
    def compute_moments_and_cgf(self, phi, mask=True):
        r"""
        Compute the moments and :math:`g(\phi)`.

        .. math::

           \overline{\mathbf{u}}  (\boldsymbol{\phi})
           &=
           \begin{bmatrix}
             \psi(\phi_1) - \psi(\sum_d \phi_{1,d})
           \end{bmatrix}
           \\
           g_{\boldsymbol{\phi}} (\boldsymbol{\phi})
           &=
           TODO
        """

        if np.any(np.asanyarray(phi) <= 0):
            raise ValueError("Natural parameters should be positive")

        sum_gammaln = np.sum(special.gammaln(phi[0]), axis=-1)
        gammaln_sum = special.gammaln(np.sum(phi[0], axis=-1))
        psi_sum = special.psi(np.sum(phi[0], axis=-1, keepdims=True))
        
        # Moments <log x>
        u0 = special.psi(phi[0]) - psi_sum
        u = [u0]
        # G
        g = gammaln_sum - sum_gammaln

        return (u, g)

    
    def compute_cgf_from_parents(self, u_alpha):
        r"""
        Compute :math:`\mathrm{E}_{q(p)}[g(p)]`
        """
        return u_alpha[1]

    
    def compute_fixed_moments_and_f(self, p, mask=True):
        r"""
        Compute the moments and :math:`f(x)` for a fixed value.

        .. math::

           u(p) =
           \begin{bmatrix}
             \log(p_1)
             \\
             \vdots
             \\
             \log(p_D)
           \end{bmatrix}

        .. math::

           f(p) = - \sum_d \log(p_d)
        """
        # Check that probabilities are non-negative
        p = np.asanyarray(p)
        if np.ndim(p) < 1:
            raise ValueError("Probabilities must be given as a vector")
        if np.any(p < 0) or np.any(p > 1):
            raise ValueError("Probabilities must be in range [0,1]")
        if not np.allclose(np.sum(p, axis=-1), 1.0):
            raise ValueError("Probabilities must sum to one")
        # Normalize probabilities
        p = p / np.sum(p, axis=-1, keepdims=True)
        # Message is log-probabilities
        logp = np.log(p)
        u = [logp]
        f = - np.sum(logp, axis=-1)
        return (u, f)

    
    def random(self, *phi, plates=None):
        r"""
        Draw a random sample from the distribution.
        """
        return random.dirichlet(phi[0], size=plates)
        

    def compute_gradient(self, g, u, phi):
        r"""
        Compute the moments and :math:`g(\phi)`.

             \psi(\phi_1) - \psi(\sum_d \phi_{1,d})

        Standard gradient given the gradient with respect to the moments, that
        is, given the Riemannian gradient :math:`\tilde{\nabla}`:

        .. math::

           \nabla &=
           \begin{bmatrix}
             (\psi^{(1)}(\phi_1) - \psi^{(1)}(\sum_d \phi_{1,d}) \nabla_1
           \end{bmatrix}
        """
        sum_phi = np.sum(phi[0], axis=-1, keepdims=True)
        d0 = g[0] * (special.polygamma(1, phi[0]) - special.polygamma(1, sum_phi))
        return [d0]


class Dirichlet(ExponentialFamily):
    r"""
    Node for Dirichlet random variables.

    The node models a set of probabilities :math:`\{\pi_0, \ldots, \pi_{K-1}\}`
    which satisfy :math:`\sum_{k=0}^{K-1} \pi_k = 1` and :math:`\pi_k \in [0,1]
    \ \forall k=0,\ldots,K-1`.

    .. math::

        p(\pi_0, \ldots, \pi_{K-1}) = \mathrm{Dirichlet}(\alpha_0, \ldots,
        \alpha_{K-1})

    where :math:`\alpha_k` are concentration parameters.

    The posterior approximation has the same functional form but with different
    concentration parameters.

    Parameters
    ----------

    alpha : (...,K)-shaped array

        Prior counts :math:`\alpha_k`

    See also
    --------

    Beta, Categorical, Multinomial, CategoricalMarkovChain
    """

    _distribution = DirichletDistribution()


    @classmethod
    def _constructor(cls, alpha, **kwargs):
        """
        Constructs distribution and moments objects.
        """
        # Number of categories
        alpha = cls._ensure_moments(alpha, DirichletPriorMoments)
        parent_moments = (alpha._moments,)

        parents = [alpha]

        categories = alpha.dims[0][0]
        moments = DirichletMoments(categories)

        return (
            parents,
            kwargs,
            moments.dims,
            cls._total_plates(kwargs.get('plates'), alpha.plates),
            cls._distribution,
            moments,
            parent_moments
        )


    def __str__(self):
        """
        Show distribution as a string
        """
        alpha = self.phi[0]
        return ("%s ~ Dirichlet(alpha)\n"
                "  alpha =\n"
                "%s" % (self.name, alpha))
