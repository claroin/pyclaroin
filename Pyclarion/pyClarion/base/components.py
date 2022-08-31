"""Basic definitions for constructing component processes."""


__all__ = [
    "Process", "Composite", "Wrapped", "Assets", "Domain", "Interface"
]


from .symbols import (
    ConstructType, Symbol, SymbolicAddress, feature, expand_address, dims
)
from .. import numdicts as nd

from typing import (
    TypeVar, Union, Tuple, Dict, Callable, Hashable, Generic, Any, Optional, 
    Text, Iterator, Iterable, Mapping, ClassVar, List, FrozenSet, Sequence, 
    Collection, Set, cast, no_type_check
)
from abc import abstractmethod
from types import SimpleNamespace, MappingProxyType
from contextlib import contextmanager
from itertools import groupby


Pt = TypeVar("Pt", bound="Process")


class Process(object):
    """A basic component process."""

    _serves: ClassVar[ConstructType] = ConstructType.null_construct

    _client: Tuple[Symbol, ...]
    _expected: Tuple[SymbolicAddress, ...]

    def __init__(self, expected: Sequence[SymbolicAddress] = None) -> None:

        self._expected = tuple(expected or ())
        self._client = ()

    def __call__(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        """
        Execute construct's forward propagation cycle.

        Pulls expected data from inputs constructs, delegates processing to 
        self.call(), and passes result to self.emit().
        """

        return self.emit(self.call(inputs))

    @property
    def client(self) -> Tuple[Symbol, ...]:
        """Client construct entrusted to self."""

        return self._client

    @property
    def expected(self) -> Tuple[SymbolicAddress, ...]:
        """Constructs from which self expects to receive activations."""

        return tuple(expand_address(self.client, x) for x in self._expected)

    def entrust(self, path: Tuple[Symbol, ...]) -> None:
        """Entrust handling of construct to self."""

        parent, construct = path[:-1], path[-1]
        if construct.ctype in type(self)._serves:
            self._client = path
        else:
            msg = "{} cannot serve constructs of type {}."
            name, ctype = type(self).__name__, repr(construct.ctype) 
            raise ValueError(msg.format(name, ctype))

    def check_inputs(self, inputs: Mapping[Any, nd.NumDict]) -> None:
        """Raise a RuntimeError if not all expected inputs are found."""

        for path in self.expected:
            if path not in inputs:
                msg = "Missing expected input from {}."
                raise RuntimeError(msg.format(path))

    def extract_inputs(
        self, inputs: Mapping[Any, nd.NumDict]
    ) -> Tuple[nd.NumDict, ...]:

        self.check_inputs(inputs)
        extracted = tuple(inputs[path] for path in self.expected)

        return extracted

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        """
        Compute construct's output.

        :param inputs: Pairs the names of input constructs with their outputs. 
        """

        return nd.NumDict(default=0)

    def emit(self, data: nd.D = None) -> nd.NumDict:
        """
        Emit output.

        If data is None, emits an empty numdict. Otherwise, emits a frozen 
        version of data. 
        
        Raises ValueError if default of data is not 0.
        """
        
        if data is None:
            return nd.NumDict(default=0.0)
        elif data.default != 0:
            msg = "Unexpected default passed to {}."
            raise ValueError(msg.format(type(self).__name__))
        elif isinstance(data, nd.NumDict):
            d = nd.squeeze(data)
            return d
        else:
            msg = "Expected NumDict instance, got {}"
            raise TypeError(msg.format(type(data).__name__))


class Composite(Process, Generic[Pt]):
    """A component process built on top of an existing process."""
    
    def __init__(
        self, base: Pt, expected: Sequence[SymbolicAddress] = None
    ) -> None:

        _expected = tuple(expected or ())

        super().__init__(expected=_expected + base._expected)

        self._expected_top = _expected
        self._base = base

    @property
    def client(self) -> Tuple[Symbol, ...]:
        """Client construct entrusted to self."""

        return self.base.client

    @property
    def base(self) -> Pt:
        """Base construct."""

        return self._base

    @property
    def expected(self) -> Tuple[SymbolicAddress, ...]:
        """
        Expected input constructs.

        Any additional constructs expected by the composite are listed first, 
        followed by those of self.base. 
        
        Equal to self.expected_top + self.base.expected.
        """

        return super().expected

    @property
    def expected_top(self) -> Tuple[SymbolicAddress, ...]:
        """Input constructs expected exclusively by the top of the composite."""

        return tuple(expand_address(self.client, x) for x in self._expected_top)

    def entrust(self, path: Tuple[Symbol, ...]) -> None:
        """Entrust handling of construct to self."""

        self.base.entrust(path)


class Wrapped(Composite[Pt]):
    """A Process wrapped by a pre- and/or post- processor."""

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        """
        Compute base construct's output.

        Feeds base construct preprocessed input and postprocesses its output.
        """

        preprocessed = self.preprocess(inputs)
        output = self.base.call(preprocessed)
        postprocessed = self.postprocess(inputs, output)
    
        return postprocessed

    def preprocess(
        self, inputs: Mapping[Any, nd.NumDict]
    ) -> Mapping[Any, nd.NumDict]:
        """Preprocess inputs to base construct."""

        return inputs

    def postprocess(
        self, inputs: Mapping[Any, nd.NumDict], output: nd.NumDict
    ) -> nd.NumDict:
        """Postprocess output of base construct."""

        return output


# @no_type_check disables type_checking for Assets (but not subclasses). 
# Included b/c dynamic usage of Assets causes mypy to complain.
# @no_type_check is not supported on mypy as of 2020-06-10. 'type: ignore' will 
# do for now. - Can
@no_type_check
class Assets(SimpleNamespace): # type: ignore
    """
    Dynamic namespace for construct assets.
    
    Provides handles for various datastructures such as chunk databases, rule 
    databases, bla information, etc. In general, all resources shared among 
    different components of a container construct are considered assets. 
    """
    pass


class Domain(object):
    """
    Domain() objects define a set of feature() symbols used in the simulation.

    Domain can be viewed as a collection of features.
    For example, if a travelling agent is simulated, part of domain might be 
    user-defined locations.
    """

    """
    Key functions:
        update(): Reflect changes of class attribute to the whole class.
        config(): Yield monitored attributes defined by _config.
                  After changes of those attributes, call update().
    """

    _config: ClassVar[Tuple[str, ...]] = ()
    """
    config is empty for class Domain, 
    but it will be filled in subclasses like Interface
    """
    
    _blocked: bool = False 
    """if '_blocked' is true, update() not autoatically called by '__setattr__()'"""
    _locked: bool = False
    """if '_locked' is true, users cannot change domain at all"""

    _features: Tuple[feature, ...]

    def __init__(self, features: Tuple[feature, ...]) -> None:
        """
        Initialize a new feature domain.

        :param features: Features belongning to the domain.
        """

        fset = set(features)
        if len(fset) < len(features):
            raise ValueError("Features may not contain duplicates.")
        if len(dims(fset)) != len(list(k for k, g in groupby(dims(features)))):
            raise ValueError("Features must be grouped by dimension.")

        self._features = features

    def __setattr__(self, name, value):
        """ignore if name is no in _config"""

        if name in type(self)._config and self._locked:
            raise RuntimeError("Cannot mutate locked domain.")
        super().__setattr__(name, value)
        if not self._blocked and name in type(self)._config:
            self.update()

    @property
    def features(self) -> Tuple[feature, ...]:
        """Domain features."""

        return self._features

    def update(self) -> None:
        """
        Set domain properties.

        Also reflect changes in domain to all relevant places
        """

        pass

    @contextmanager
    def config(self): 
        """
        Update self after adjustments to monitored attributes defined by _config.

        update() is not called during adjustments
        """

        self._blocked = True
        yield
        self._blocked = False
        self.update()

    def lock(self): 
        """Disallow mutation of domain."""

        self._locked = True

    def disjoint(*domains: "Domain") -> bool: 
        """Return True iff domains have no overlap."""

        # NOTE: This method does not have a self argument, but works both as an 
        # instance and class method. This is similar to set.union and 
        # set.intersection.

        if len(domains) == 0:
            raise ValueError("disjoint() doesn't accept 0 argument")
        elif len(domains) == 1:
            """
            Since Domain class doesn't allow duplicate features,
            when there's only one domain, certainly no overlap
            """
            return True

        s = set.intersection(*(set(dom.features) for dom in domains))

        return s == set()

    # TO DO: add set operation?


class Interface(Domain):
    """A feature domain defining a control interface."""

    _cmds: Tuple[feature, ...]
    _defaults: Tuple[feature, ...]
    _params: Tuple[feature, ...]
    _flags: Tuple[feature, ...]

    def __init__(
        self, 
        cmds: Tuple[feature, ...] = (), 
        params: Tuple[feature, ...] = (), 
        flags: Tuple[feature, ...] = (),
        extras: Tuple[feature, ...] = ()
    ) -> None:
        """
        Initialize a new interface.

        :param cmds: Command features.
        :param params: Command parameters.
        :param flags: Command flags.
        :param extras: Any additional features.
        """

        # TODO: Enforce fuzzy datatype for cmds when datatype markers are added.

        if dims(set(cmds)) & dims(set(params)):
            raise ValueError("Cmds and params may not share dims.")
        if dims(set(cmds)) & dims(set(flags)):
            raise ValueError("Cmds and flags may not share dims.")
        if dims(set(cmds)) & dims(set(extras)):
            raise ValueError("Cmds and extras may not share dims.")
        if dims(set(params)) & dims(set(flags)):
            raise ValueError("Params and flags may not share dims.")
        if dims(set(params)) & dims(set(extras)):
            raise ValueError("Params and extras may not share dims.")
        if dims(set(flags)) & dims(set(extras)):
            raise ValueError("Flags and extras may not share dims.")

        super().__init__(features=(cmds + params + flags + extras))

        self._cmds = cmds
        self._params = params
        self._flags = flags
        self._extras = extras

        key = feature.dim.fget # type: ignore
        self._defaults = tuple(next(g) for k, g in groupby(self.cmds, key))

    @property
    def cmds(self) -> Tuple[feature, ...]:
        """Interface commands."""

        return self._cmds

    @property
    def params(self) -> Tuple[feature, ...]:
        """Interface params."""

        return self._params

    @property
    def flags(self) -> Tuple[feature, ...]:
        """Interface flags."""

        return self._flags

    @property
    def extras(self) -> Tuple[feature, ...]:
        """Additional features associated with interface."""

        return self._extras

    @property
    def defaults(self) -> Tuple[feature, ...]:
        """
        Default commands.
        
        The default command is the first listed value in each dimension.
        """

        return self._defaults

    def parse_commands(self, data: nd.NumDict) -> Tuple[feature, ...]:
        """
        Determine the value associated with each control dimension.
        
        :param data: A set of features.
        """

        if data.default != 0.0:
            raise ValueError("Unexpected default strength.")

        data = nd.squeeze(data)
        data = nd.keep(data, keys=self.cmds)
        if any(v != 1.0 for v in data.values()):
            raise ValueError("Encountered non-integral cmd strength.")

        cmds = tuple(f for f in self.cmds if f in data)
        if len(cmds) > len(set(dims(self.cmds))):
            raise ValueError("Encountered multiple values from a single dim.")

        parse = list(self.defaults)
        cmd_dims = dims(parse)
        for cmd in cmds:
            i = cmd_dims.index(cmd.dim)
            parse[i] = cmd

        return tuple(parse)
