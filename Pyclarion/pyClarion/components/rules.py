"""Tools for creating, managing, and processing rules."""


__all__ = ["Rule", "Rules", "AssociativeRules", "ActionRules"]


from ..base.symbols import ConstructType, Symbol, rule, chunk
from ..base.components import Process
from .chunks_ import Chunks
from .. import numdicts as nd

from typing import (
    Mapping, MutableMapping, TypeVar, Generic, Type, Dict, FrozenSet, Set, 
    Tuple, overload, cast, Any, Iterator, Sequence, Union
)
from contextlib import contextmanager
from types import MappingProxyType


class Rule(object):
    """Represents a rule form."""

    __slots__ = ("_conc", "_weights")

    def __init__(
        self, conc: chunk, *conds: chunk, weights: Dict[chunk, float] = None
    ):
        """
        Initialize a new rule.

        If conditions contains items that do not appear in weights, weights is 
        extended to map each of these items to a weight of 1. If weights is 
        None, every cond is assigned a weight of 1. 

        If the weights sum to more than 1.0, they are renormalized such that 
        each weight w is mapped to w / sum(weights.values()).

        :param conclusion: A chunk symbol for the rule conclusion.
        :param conditions: A sequence of chunk symbols representing rule 
            conditions.
        :param weights: An optional mapping from condition chunk symbols 
            to condition weights.
        """

        # preconditions
        if weights is not None:
            if not set(conds).issuperset(weights): 
                ValueError("Keys of arg `weights` do not match conds.")
            if not all(0 < v for v in weights.values()):
                ValueError("Weights must be strictly positive.")

        ws = nd.MutableNumDict(weights)
        ws.extend(conds, value=1.0)

        w_sum = nd.val_sum(ws)
        if w_sum > 1.0: 
            ws /= w_sum

        self._conc = conc
        self._weights = nd.freeze(ws)

        # postconditions
        assert set(self._weights) == set(conds), "Each cond must have a weight."
        assert nd.val_sum(ws) <= 1, "Inferred weights must sum to one or less."

    def __repr__(self) -> str:

        return "Rule(conc={}, weights={})".format(self.conc, self.weights)

    def __eq__(self, other) -> bool:

        if isinstance(other, Rule):
            b = (
                self.conc == other.conc and 
                nd.isclose(self.weights, other.weights)
            )
            return b
        else:
            return NotImplemented

    @property
    def conc(self) -> chunk:
        """Conclusion of rule."""

        return self._conc

    @property
    def weights(self) -> nd.NumDict:
        """Conditions and condition weights of rule."""

        return self._weights

    def match(self, other: "Rule") -> bool:
        """ If conclusion matches and numDict is close, return True"""

        b = (
            self.conc == other.conc
            and nd.isclose(self.weights, other.weights)
        )

        return b

    def strength(self, strengths: nd.NumDict) -> float:
        """
        Compute rule strength given condition strengths.
        
        The rule strength is computed as the weighted sum of the condition 
        strengths in strengths.

        Implementation based on p. 60 and p. 73 of Anatomy of the Mind.
        """

        weighted = nd.keep(strengths, keys=self.weights) * self.weights
        
        return nd.val_sum(weighted)

    def support(self, *cdbs: Chunks) -> bool:
        """
        Return True iff cdbs support all rules in self.
        
        A set of cdbs is considered to support a rule if every condition and 
        conclusion of the rule is in at least one of the cdbs.
        """

        val = all(any(c in d for d in cdbs) for c in (self.conc, *self.weights))
        
        return val


Rt = TypeVar("Rt", bound="Rule")
class Rules(MutableMapping[rule, Rt], Generic[Rt]):
    """A simple rule database."""

    @overload
    def __init__(self: "Rules[Rule]") -> None:
        ...

    @overload
    def __init__(self: "Rules[Rule]", *, max_conds: int) -> None:
        ...

    @overload
    def __init__(self, *, rule_type: Type[Rt]) -> None:
        ...

    @overload
    def __init__(self, *, max_conds: int, rule_type: Type[Rt]) -> None:
        ...

    @overload
    def __init__(
        self, data: Mapping[rule, Rt], max_conds: int, rule_type: Type[Rt]
    ) -> None:
        ...

    def __init__(
        self, 
        data: Mapping[rule, Rt] = None,
        max_conds: int = None,
        rule_type: Type[Rt] = None
    ) -> None:

        if data is None:
            data = dict()
        else:
            data = dict(data)

        self._data = data
        self._cdbs: Tuple[Chunks, ...] = ()
        self._enforce_support = False

        self.max_conds = max_conds
        self.Rule: Type[Rt] = rule_type if rule_type is not None else Rule

        self._add_promises: MutableMapping[rule, Rt] = dict()
        self._del_promises: Set[rule] = set()

    def __repr__(self) -> str:

        repr_ = "{}({})".format(type(self).__name__, repr(self._data))
        return repr_

    def __len__(self) -> int:

        return len(self._data)

    def __iter__(self) -> Iterator[rule]:

        yield from iter(self._data)

    def __getitem__(self, key: Any) -> Rt:

        return self._data[key]

    def __setitem__(self, key: Any, val: Any) -> None:

        self._validate_rule_form(val)
        if isinstance(val, self.Rule):
            if self._enforce_support and not val.support(*self._cdbs):
                msg = "Rule {} contains unexpected chunks."
                raise ValueError(msg.format(key.cid))
            self._data[key] = val
        else:
            msg = "This rule database expects rules of type '{}'." 
            TypeError(msg.format(type(self.Rule.__name__)))

    def __delitem__(self, key: Any) -> None:

        del self._data[key]

    @property
    def add_promises(self) -> Mapping[rule, Rt]:
        """A view of promised additions."""

        return MappingProxyType(self._add_promises)

    @property
    def del_promises(self) -> FrozenSet[rule]:
        """A view of promised deletions."""

        return frozenset(self._del_promises)

    def define(
        self, 
        r: rule, 
        conc: chunk, 
        *conds: chunk, 
        weights: Dict[chunk, float] = None
    ) -> rule:
        """
        Add a new rule.
        
        Returns the rule symbol.
        """

        self[r] = self.Rule(conc, *conds, weights=weights)

        return r
    
    @overload
    def match(self, obj: Rule, check_promises: bool) -> Set[rule]:
        pass

    @overload
    def match(self, obj: Sequence[chunk], check_promises: bool) -> Set[rule]:
        pass

    def match(self, obj: Union[Rule, Sequence[chunk]], check_promises: bool = True) -> Set[rule]:
        """ Returns a set of rules matching the given rule or sequence of chunks"""

        if isinstance(obj, Rule):
            target = obj
        else:
            target = Rule(*obj)

        rules = set()
        for ch, form_ch in self.items():
            if form_ch.match(target):
                rules.add(ch)
        if check_promises:
            for ch, form_ch in self._add_promises.items():
                if form_ch.match(target):
                    rules.add(ch)

        return rules

    def contains_form(self, form) -> bool:
        """
        Check if the rule set contains a given rule form.
        
        See Rule for details on rule forms.
        """

        return any(form == entry for entry in self.values())

    @contextmanager
    def enforce_support(self, *cdbs: Chunks):
        """
        Reject new rules that are not supported by cdbs.
        
        Use this method as a context manager when initializing complex 
        knowledge to automatically check for coding errors.
        """

        self._cdbs = cdbs
        self._enforce_support = True
        yield
        self._enforce_support = False
        self._cdbs = ()

    def request_add(self, r: rule, form: Rt) -> None:
        """
        Inform self of a new rule to be applied at a later time.
        
        Adds the new rule on call to self.step().
        
        If r is already member of self, will overwrite the existing rule. Does 
        not check for duplicate forms. 
        
        If an update is already registered for rule r, will throw an error.

        Does not validate the rule form before registering the request. 
        Validation occurs at update time. 
        """

        if r in self._add_promises or r in self._del_promises:
            msg = "Rule {} already registered for a promised update."
            raise ValueError(msg.format(r))
        else:
            self._add_promises[r] = form

    def request_del(self, r: rule) -> None:
        """
        Inform self of an existing rule to be removed at update time.

        The rule will be removed on call to step(). 
         
        If r is not already a member of self, will raise an error.
        """

        if r in self._add_promises or r in self._del_promises:
            msg = "Rule {} already registered for a promised update."
            raise ValueError(msg.format(r))
        elif r not in self:
            raise ValueError("Cannot delete non-existent rule.")
        else:
            self._del_promises.add(r)

    def step(self) -> None:
        """Apply any promised updates."""

        for r in self._del_promises:
            del self[r]
        self._del_promises.clear()

        self.update(self._add_promises)
        self._add_promises.clear()

    def _validate_rule_form(self, form):

        if self.max_conds is not None and len(form.weights) > self.max_conds:
            msg = "Received rule with {} conditions; maximum allowed is {}."
            raise ValueError(msg.format(len(form.weights), self.max_conds))


class RuleDBUpdater(Process):
    """Applies requested updates to a client Rules instance."""

    _serves = ConstructType.updater

    def __init__(self, rules: "Rules") -> None:
        """Initialize a Rules.Updater instance."""

        super().__init__()
        self.rules = rules

    def __call__(
        self, inputs: Mapping[Tuple[Symbol, ...], nd.NumDict]
    ) -> nd.NumDict:
        """Resolve all outstanding rule database update requests."""

        self.rules.step()

        return super().call(inputs)


class AssociativeRules(Process):
    """
    Propagates activations among chunks through associative rules.
    
    The strength of the conclusion is calculated as a weighted sum of condition 
    strengths. In cases where there are multiple rules with the same conclusion, 
    the maximum is taken. 

    Implementation based on p. 73-74 of Anatomy of the Mind.
    """

    _serves = ConstructType.flow_tt

    def __init__(self, source: Symbol, rules: Rules) -> None:

        super().__init__(expected=(source,))
        self.rules = rules

    def call(
        self, inputs: Mapping[Tuple[Symbol, ...], nd.NumDict]
    ) -> nd.NumDict:

        strengths, = self.extract_inputs(inputs)

        d = nd.MutableNumDict(default=0.0)
        for r, form in self.rules.items():
            s_r = form.strength(strengths)
            d[form.conc] = max(d[form.conc], s_r)
            d[r] = s_r
        d.squeeze()

        assert d.default == 0, "Unexpected output default."

        return d


class ActionRules(Process):
    """
    Propagates activations from condition to action chunks using action rules.
    
    Action rules compete to be selected based on their rule strengths, which is 
    equal to the product of an action rule's weight and the strength of its 
    condition chunk. The rule strength of the selected action is then 
    propagated to its conclusion. 
    """

    _serves = ConstructType.flow_tt

    def __init__(
        self, 
        source: Symbol, 
        rules: Rules, 
        threshold: float = 0.0,
        temperature: float = .01
    ) -> None:

        if rules.max_conds is None or rules.max_conds > 1:
            msg = "Rule database must not accept multiple condition rules."
            raise ValueError(msg)

        super().__init__(expected=(source,))
        self.rules = rules
        self.threshold = threshold
        self.temperature = temperature

    def call(
        self, inputs: Mapping[Tuple[Symbol, ...], nd.NumDict]
    ) -> nd.NumDict:

        strengths, = self.extract_inputs(inputs)
        strengths = nd.threshold(
            strengths, th=self.threshold, keep_default=True
        )

        d = nd.MutableNumDict(default=0)
        for r, form in self.rules.items():
            d[r] = form.strength(strengths)
        
        probabilities = nd.boltzmann(d, self.temperature)
        selection = nd.draw(probabilities, n=1)

        d *= selection
        d.squeeze()
        d.max(nd.transform_keys(d, func=lambda r: self.rules[r].conc))

        # postcondition
        assert d.default == 0, "Unexpected output default."

        return d
