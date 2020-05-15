""" Builds the template table in markdown format for README.md """

from osxphotos.photoinfo.template import (
    TEMPLATE_SUBSTITUTIONS,
    TEMPLATE_SUBSTITUTIONS_MULTI_VALUED,
)

print("| Substitution | Description |")
print("|--------------|-------------|")
for subst, descr in [
    *TEMPLATE_SUBSTITUTIONS.items(),
    *TEMPLATE_SUBSTITUTIONS_MULTI_VALUED.items(),
]:
    print(f"|{subst}|{descr}|")
