"""test_dfa.py — checks every operation against its theoretical definition.  Run: python test_dfa.py"""
import itertools, unittest
import dfa_logic as L

STRINGS = [""] + ["".join(t) for n in range(1, 8) for t in itertools.product("01", repeat=n)]  # ε .. length 7
EX = [e["m"] for e in L.EXAMPLES]
LOGIC = {"union": lambda a, b: a or b, "intersection": lambda a, b: a and b, "difference": lambda a, b: a and not b}
acc = lambda m, s: L.run(m, s)["accepted"]


class Tests(unittest.TestCase):
    def test_product_ops_match_logic(self):
        for op, f in LOGIC.items():
            for A, B in itertools.product(EX, EX):
                R = L.build(A, B, op)["machine"]
                for s in STRINGS:
                    self.assertEqual(acc(R, s), f(acc(A, s), acc(B, s)), (op, s))

    def test_complement_reverses(self):
        for A in EX:
            R = L.build(A, None, "complement")["machine"]
            for s in STRINGS:
                self.assertNotEqual(acc(R, s), acc(A, s))

    def test_different_sizes_and_multiple_accepting(self):
        multi = {"states": ["a", "b", "c"], "alphabet": ["0", "1"], "start": "a", "accept": ["b", "c"],
                 "delta": {"a": {"0": "b", "1": "c"}, "b": {"0": "b", "1": "a"}, "c": {"0": "c", "1": "c"}}}
        R = L.build(multi, EX[0], "union")["machine"]
        for s in STRINGS:
            self.assertEqual(acc(R, s), acc(multi, s) or acc(EX[0], s))

    def test_state_without_outgoing_transitions(self):
        # B is accepting and has NO outgoing transitions: language = {"0"}
        A = {"states": ["A", "B"], "alphabet": ["0", "1"], "start": "A", "accept": ["B"],
             "delta": {"A": {"0": "B"}, "B": {}}}
        out = L.build(A, A, "union")
        self.assertTrue(out["notes"] and "machine" in out)
        for s in STRINGS:
            self.assertEqual(acc(out["machine"], s), s == "0")
        comp = L.build(A, None, "complement")["machine"]       # complement must accept everything except "0"
        for s in STRINGS:
            self.assertEqual(acc(comp, s), s != "0")

    def test_errors_and_invalid_symbol(self):
        self.assertIn("error", L.run(EX[0], "1a0"))
        self.assertTrue(L.run(EX[0], "")["accepted"] is False)           # ε on 'ends in 0'
        other = dict(EX[1], alphabet=["0", "1", "2"])
        self.assertIn("errors", L.build(EX[0], other, "union"))
        self.assertIn("errors", L.build({**EX[0], "start": ""}, EX[1], "union"))
        bad = {**EX[0], "states": ["q0", "(q1"], "accept": ["(q1"]}            # would collide with pair names
        self.assertIn("errors", L.build(bad, EX[1], "union"))

    def test_other_alphabet(self):
        # over {a, b}: A = "has an a", B = "ends in b" (B has a missing transition -> trap state)
        A = {"states": ["n", "y"], "alphabet": ["a", "b"], "start": "n", "accept": ["y"],
             "delta": {"n": {"a": "y", "b": "n"}, "y": {"a": "y", "b": "y"}}}
        B = {"states": ["s", "e"], "alphabet": ["b", "a"], "start": "s", "accept": ["e"],
             "delta": {"s": {"a": "s", "b": "e"}, "e": {"b": "e"}}}
        words = [""] + ["".join(t) for n in range(1, 6) for t in itertools.product("ab", repeat=n)]
        for op, f in LOGIC.items():
            out = L.build(A, B, op)
            Ac, Bc = out["parts"]["A"], out["parts"]["B"]
            for s in words:
                self.assertEqual(acc(out["machine"], s), f(acc(Ac, s), acc(Bc, s)), (op, s))

    def test_language_info(self):
        info = L.build(EX[1], None, "complement")["info"]          # odd number of 1s
        self.assertEqual((info["accepted"], info["rejected"], info["pairs"]), ("1", "", None))
        empty = L.build(EX[0], L.build(EX[0], None, "complement")["machine"], "intersection")["info"]
        self.assertIsNone(empty["accepted"])                        # L ∩ complement(L) = ∅
        full = L.build(EX[0], L.build(EX[0], None, "complement")["machine"], "union")["info"]
        self.assertIsNone(full["rejected"])                         # L ∪ complement(L) = Σ*
        self.assertEqual(L.build(EX[0], EX[2], "union")["info"]["pairs"], 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
