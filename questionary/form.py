from collections import namedtuple
from typing import Callable, Union

from questionary.constants import DEFAULT_KBI_MESSAGE
from questionary.question import Question, FrozenOperationMixin

FormField = namedtuple("FormField", ["key", "question"])


def form(**kwargs: Question):
    """Create a form with multiple questions.

    The parameter name of a question will be the key for the answer in
    the returned dict."""
    return Form(*(FormField(k, q) for k, q in kwargs.items()))


class DependencyError(Exception):
    pass


class Form:
    """Multi question prompts. Questions are asked one after another.

    All the answers are returned as a dict with one entry per question."""

    def __init__(self, *form_fields: FormField):
        self.form_fields = form_fields
        self.skip_conditions = {}

    def skip_if(self, **conditions: Union[Callable, FrozenOperationMixin]):
        for k, condition in conditions.items():
            self.skip_conditions[k] = condition
        return self

    def unsafe_ask(self, patch_stdout=False):
        answers = {}
        previous_count = 0
        while not all(f.key in answers for f in self.form_fields):
            for field in self.form_fields:
                if field.key in answers:
                    def skip(x): return True
                else:
                    skip = self.skip_conditions.get(field.key, lambda x: False)
                values = {f.question: answers[f.key] for f in self.form_fields
                          if f.key in answers}
                values.update(answers)  # question and keys as keys in values
                try:
                    if not skip(values):
                        answer = field.question.unsafe_ask(patch_stdout)
                        answers[field.key] = answer
                    else:
                        answers[field.key] = field.question.default
                except KeyError:
                    # if the skip_if requires another question's answer,
                    # loop until we have that required answer
                    continue
            else:
                if previous_count == len(answers):
                    raise DependencyError("Dependencies in conditional "
                                          "skip_if cannot be resolved. "
                                          "please make sure there are no "
                                          "circular dependencies in your "
                                          "skip_if conditions")
                previous_count = len(answers)
        return answers

    def ask(self, patch_stdout=False, kbi_msg=DEFAULT_KBI_MESSAGE):
        try:
            return self.unsafe_ask(patch_stdout)
        except KeyboardInterrupt:
            print('')
            print(kbi_msg)
            print('')
            return {}
