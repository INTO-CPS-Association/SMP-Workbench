from enum import Enum

class Distribution(Enum):
    NORMAL = "normal"
    EXPONENTIAL = "exponential"
    UNIFORM = "uniform"
    BINOMIAL = "binomial"
    POISSON = "poisson"
    BERNOULLI = "bernoulli"
    GAMMA = "gamma"
    BETA = "beta"
    LOGNORMAL = "lognormal"
    WEIBULL = "weibull"
    NONE = "none"