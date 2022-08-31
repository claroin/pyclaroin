from pyClarion import base as clb
from pyClarion import numdicts as nd

import unittest
from unittest import mock


class TestRealizerMethods(unittest.TestCase):

    def test_init_accepts_name_of_type_Symbol(self):

        clb.Realizer(name=clb.Symbol("chunks", 1))

    def test_init_rejects_name_of_type_other_than_Symbol(self):        

        with self.assertRaises(TypeError):
            clb.Realizer(name="My Realizer")


@mock.patch.object(clb.Process, "_serves", clb.ConstructType.basic_construct)
class TestStructureMethods(unittest.TestCase):

    def tearDown(self):

        self.assertEqual(
            clb.realizers.BUILD_CTX.get(), 
            (), 
            "BUILD_CTX cleanup failed."
        )

    def test_assembly_sequence_is_recorded_correctly(self):

        nacs = clb.Structure(
            name=clb.subsystem("nacs"),
            assets=None
        )

        with nacs:

            clb.Construct(
                name=clb.chunks("in"),
                process=clb.Process()
            )

            clb.Construct(
                name=clb.flow_tt("associative_rules"),
                process=clb.Process()
            )
            clb.Construct(
                name=clb.chunks("out"),
                process=clb.Process()
            )

            clb.Construct(
                name=clb.terminus("selection"),
                process=clb.Process()
            )

        expected = (
            clb.chunks("in"),
            clb.flow_tt("associative_rules"),
            clb.chunks("out"),
            clb.terminus("selection")
        )

        self.assertEqual(tuple(iter(nacs)), expected)

    def test_assembly_sequence_is_recorded_correctly_in_nested_mode(self):

        agent = clb.Structure(
            name=clb.agent("agent"),
            assets=None
        )

        with agent:

            clb.Construct(
                name=clb.buffer("sensory"),
                process=clb.Process()
            )

            clb.Construct(
                name=clb.buffer("wm"),
                process=clb.Process()
            )

            nacs = clb.Structure(
                name=clb.subsystem("nacs"),
                assets=None
            )

            with nacs:

                clb.Construct(
                    name=clb.chunks("in"),
                    process=clb.Process()
                )

                clb.Construct(
                    name=clb.flow_tt("associative_rules"),
                    process=clb.Process()
                )
                clb.Construct(
                    name=clb.chunks("out"),
                    process=clb.Process()
                )

                clb.Construct(
                    name=clb.terminus("selection"),
                    process=clb.Process()
                )

        agent_expected = (
            clb.buffer("sensory"),
            clb.buffer("wm"),
            clb.subsystem("nacs")
        )

        nacs_expected = (
            clb.chunks("in"),
            clb.flow_tt("associative_rules"),
            clb.chunks("out"),
            clb.terminus("selection")
        )

        self.assertEqual(tuple(iter(agent)), agent_expected)
        self.assertEqual(tuple(iter(nacs)), nacs_expected)

    def test_assembly_fails_on_missing_link_target(self):

        with self.assertRaises(RuntimeError):

            agent = clb.Structure(
                name=clb.agent("agent"),
                assets=None
            )

            with agent:

                nacs = clb.Structure(
                    name=clb.subsystem("nacs"),
                    assets=None
                )

                with nacs:

                    clb.Construct(
                        name=clb.chunks("in"),
                        process=clb.Process(
                            expected=[
                                (
                                    clb.agent("agent"),
                                    clb.buffer("wm")
                                )
                            ]
                        )
                    )
        
    def test_assembly_links_constructs_correctly(self):

        agent = clb.Structure(
            name=clb.agent("agent"),
            assets=None
        )

        with agent:

            clb.Construct(
                name=clb.buffer("wm"),
                process=clb.Process()
            )

            nacs = clb.Structure(
                name=clb.subsystem("nacs"),
                assets=None
            )

            with nacs:

                clb.Construct(
                    name=clb.chunks("in"),
                    process=clb.Process(
                        expected=[
                            (
                                clb.agent("agent"),
                                clb.buffer("wm")
                            )
                        ]
                    )
                )

                clb.Construct(
                    name=clb.flow_tt("associative_rules"),
                    process=clb.Process(
                        expected=[
                            (
                                clb.agent("agent"),
                                clb.subsystem("nacs"),
                                clb.chunks("in")
                            )
                        ]
                    )
                )

                clb.Construct(
                    name=clb.chunks("out"),
                    process=clb.Process(
                        expected=[
                            (
                                clb.agent("agent"),
                                clb.subsystem("nacs"),
                                clb.chunks("in")
                            ),
                            (
                                clb.agent("agent"),
                                clb.subsystem("nacs"),
                                clb.flow_tt("associative_rules")
                            )
                        ]
                    )
                )

                clb.Construct(
                    name=clb.terminus("selection"),
                    process=clb.Process(
                        expected=[
                            (
                                clb.agent("agent"),
                                clb.subsystem("nacs"),
                                clb.chunks("out")
                            )
                        ]
                    )
                )
        
        self.assertEqual(
            set(agent[clb.buffer("wm")].inputs),
            set()
        )

        self.assertEqual(
            set(nacs[clb.chunks("in")].inputs),
            {
                (clb.agent("agent"), clb.buffer("wm"))
            }
        )

        self.assertEqual(
            set(nacs[clb.flow_tt("associative_rules")].inputs),
            {
                (
                    clb.agent("agent"),
                    clb.subsystem("nacs"),
                    clb.chunks("in")
                )
            }
        )

        self.assertEqual(
            set(nacs[clb.chunks("out")].inputs),
            {
                (
                    clb.agent("agent"),
                    clb.subsystem("nacs"),
                    clb.chunks("in")
                ),
                (
                    clb.agent("agent"),
                    clb.subsystem("nacs"),
                    clb.flow_tt("associative_rules")
                )
            }
        )

        self.assertEqual(
            set(nacs[clb.terminus("selection")].inputs),
            {
                (
                    clb.agent("agent"),
                    clb.subsystem("nacs"),
                    clb.chunks("out")
                )
            }
        )

    def test_structure_output_is_correctly_formed(self):

        agent = clb.Structure(
            name=clb.agent("agent"),
            assets=None
        )

        with agent:

            clb.Construct(
                name=clb.buffer("sensory"),
                process=clb.Process()
            )

            clb.Construct(
                name=clb.buffer("wm"),
                process=clb.Process()
            )

            nacs = clb.Structure(
                name=clb.subsystem("nacs"),
                assets=None
            )

            with nacs:

                clb.Construct(
                    name=clb.chunks("in"),
                    process=clb.Process()
                )

                clb.Construct(
                    name=clb.flow_tt("associative_rules"),
                    process=clb.Process()
                )
                clb.Construct(
                    name=clb.chunks("out"),
                    process=clb.Process()
                )

                clb.Construct(
                    name=clb.terminus("selection"),
                    process=clb.Process()
                )

        nacs_expected = {
            clb.chunks("in"): nd.NumDict(default=0),
            clb.flow_tt("associative_rules"): nd.NumDict(default=0),
            clb.chunks("out"): nd.NumDict(default=0),
            clb.terminus("selection"): nd.NumDict(default=0)
        }

        agent_expected = {
            clb.buffer("sensory"): nd.NumDict(default=0),
            clb.buffer("wm"): nd.NumDict(default=0),
            (clb.subsystem("nacs"), clb.chunks("in")): nd.NumDict(default=0),
            (clb.subsystem("nacs"), clb.flow_tt("associative_rules")): nd.NumDict(default=0),
            (clb.subsystem("nacs"), clb.chunks("out")): nd.NumDict(default=0),
            (clb.subsystem("nacs"), clb.terminus("selection")): nd.NumDict(default=0)
        }

        self.assertEqual(nacs.output, nacs_expected, "failed on nacs")
        self.assertEqual(agent.output, agent_expected, "failed on agent")
        
    def test_assembly_fails_reentering_a_structure(self):

        with self.assertRaises(RuntimeError):

            agent = clb.Structure(
                name=clb.agent("agent"),
                assets=None
            )

            with agent:

                nacs = clb.Structure(
                    name=clb.subsystem("nacs"),
                    assets=None
                )

                with nacs:

                    clb.Construct(
                        name=clb.chunks("in"),
                        process=clb.Process()
                    )
                
                with nacs:

                    clb.Construct(
                        name=clb.chunks("out"),
                        process=clb.Process()
                    )

    def test_assembly_succeeds_on_good_nested_sturcture_pull(self):

        agent = clb.Structure(
            name=clb.agent("agent"),
            assets=None
        )

        with agent:

            clb.Construct(
                name=clb.buffer("wm"),
                process=clb.Process(
                    expected=[
                        (
                            clb.agent("agent"),
                            clb.subsystem("acs"), 
                            clb.terminus("wm")
                        )
                    ]
                )
            )

            acs = clb.Structure(
                name=clb.subsystem("acs"),
                assets=None
            )

            with acs:

                clb.Construct(
                    name=clb.terminus("wm"),
                    process=clb.Process()
                )
        
    def test_assembly_fails_on_bad_nested_sturcture_pull(self):

        with self.assertRaises(RuntimeError):

            agent = clb.Structure(
                name=clb.agent("agent"),
                assets=None
            )

            with agent:

                clb.Construct(
                    name=clb.buffer("wm"),
                    process=clb.Process(
                        expected=[
                            (
                                clb.agent("agent"),
                                clb.subsystem("acs"), 
                                clb.terminus("wm")
                            )
                        ]
                    )
                )

                acs = clb.Structure(
                    name=clb.subsystem("acs"),
                    assets=None
                )

                with acs:

                    clb.Construct(
                        name=clb.terminus("not_wm"),
                        process=clb.Process()
                    )

    def test_step_calls_are_correctly_sequenced(self):

        recorded = []
        
        def call_recorder(self, inputs):

            recorded.append(self.client)

            return nd.NumDict(default=0)

        with mock.patch.object(clb.Process, "call", call_recorder):

            agent = clb.Structure(
                name=clb.agent("agent"),
                assets=None
            )

            with agent:

                clb.Construct(
                    name=clb.buffer("wm"),
                    process=clb.Process(
                        expected=[
                            (
                                clb.agent("agent"),
                                clb.subsystem("acs"), 
                                clb.terminus("wm")
                            ),
                            (
                                clb.agent("agent"),
                                clb.subsystem("nacs"), 
                                clb.terminus("out")
                            )
                        ]
                    )
                )

                acs = clb.Structure(
                    name=clb.subsystem("acs"),
                    assets=None
                )

                with acs:

                    clb.Construct(
                        name=clb.terminus("wm"),
                        process=clb.Process()
                    )

                nacs = clb.Structure(
                    name=clb.subsystem("nacs"),
                    assets=None
                )

                with nacs:

                    clb.Construct(
                        name=clb.chunks("out"),
                        process=clb.Process(
                            expected=[
                                (clb.agent("agent"), clb.buffer("wm"))
                            ]
                        )
                    )

                    clb.Construct(
                        name=clb.terminus("out"),
                        process=clb.Process(
                            expected=[
                                (
                                    clb.agent("agent"),
                                    clb.subsystem("nacs"),
                                    clb.chunks("out")
                                )
                            ]
                        )
                    )

            agent.step()

            expected = [
                (clb.agent("agent"), clb.buffer("wm")),
                (clb.agent("agent"), clb.subsystem("acs"), clb.terminus("wm")),
                (clb.agent("agent"), clb.subsystem("nacs"), clb.chunks("out")),
                (clb.agent("agent"), clb.subsystem("nacs"), clb.terminus("out"))
            ]
            
            self.assertEqual(expected, recorded)

    def test_assembly_limited_to_2_levels_of_nesting(self):

        with self.assertRaises(RuntimeError):
            agent = clb.Structure(name=clb.agent("A"))
            with agent:
                buffer = clb.Construct(name=clb.buffer("B"), process=clb.Process())
                subsys = clb.Structure(name=clb.subsystem("S1"))
                with subsys:
                    subsys2 = clb.Structure(name=clb.subsystem("S2"))
                    with subsys2:
                        pool = clb.Construct(name=clb.chunks("C"), process=clb.Process())

