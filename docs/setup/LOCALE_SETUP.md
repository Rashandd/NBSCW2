# Locale Setup and Translation Management

This guide explains how to manage translations and locale files in the Rashigo project.

## Overview

The project supports multiple languages:
- English (en)
- Turkish (tr)
- Spanish (es)
- French (fr)
- German (de)

Translation files are located in `python_version/locale/`.

## Regenerating Translation Files

If you need to regenerate translation files (e.g., after removing unused directories or cleaning up references):

### 1. Extract translatable strings

```bash
cd python_version
python manage.py makemessages -l en
python manage.py makemessages -l tr
python manage.py makemessages -l es
python manage.py makemessages -l fr
python manage.py makemessages -l de
```

Or extract for all languages at once:

```bash
python manage.py makemessages -a
```

### 2. Edit translation files

Edit the `.po` files in `locale/<language>/LC_MESSAGES/django.po` to add translations.

### 3. Compile translations

After editing, compile the translations:

```bash
python manage.py compilemessages
```

This creates `.mo` files from `.po` files. The `.mo` files are compiled and should not be committed to version control (they're in `.gitignore`).

## Cleaning Up Translation Files

If translation files contain references to removed directories (like `social_empires`), you can:

1. **Regenerate from scratch** (recommended):
   ```bash
   # Remove old .po files
   rm -rf locale/*/LC_MESSAGES/django.po
   
   # Regenerate
   python manage.py makemessages -a
   ```

2. **Manually edit** the `.po` files to remove unwanted references in the `#:` comment lines.

## Translation Workflow

1. Mark strings for translation in code using `gettext` or `_()`:
   ```python
   from django.utils.translation import gettext as _
   
   message = _("Hello, world!")
   ```

2. Extract strings: `python manage.py makemessages -a`

3. Translate strings in `.po` files

4. Compile: `python manage.py compilemessages`

5. Test: Restart the server and test translations

## Notes

- `.po` files (source) should be committed to version control
- `.mo` files (compiled) should NOT be committed (they're auto-generated)
- Always regenerate translations after major code changes
- Keep translation files in sync across all languages

