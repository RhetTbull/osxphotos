""" Builds the template table in markdown format for README.md """

from osxphotos.template import TEMPLATE_SUBSTITUTIONS

print("| Substitution | Description |")
print("|--------------|-------------|")
for subst, descr in TEMPLATE_SUBSTITUTIONS.items():
    print(f"|{subst}|{descr}|")
