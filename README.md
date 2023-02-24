# Things to update in new repo:

```
.wakatime-project
.github/settings.yml
.github/dependabot.yml
README.md
```

---

# Github documentation regarding .gitattributes
https://docs.github.com/en/get-started/getting-started-with-git/configuring-git-to-handle-line-endings#per-repository-settings

---

# Template repos for gitattributes
https://github.com/alexkaratarakis/gitattributes

---

# CI to check gitattribute files in a repo:

```
missing_attributes=$(git ls-files | git check-attr -a --stdin | grep "text eol=lf")
if [[ "$missing_attributes" ]]; then
  echo ".gitattributes rule missing for the following files:";
  echo "$missing_attributes";
else
  echo "All files have a corresponding rule in .gitattributes";
fi
```

---

# Renormalize files in a repo:

```
git add . -u
git commit -m "Saving files before refreshing line endings"
git add --renormalize .
git status
git commit -m "Normalize all the line endings"
```
