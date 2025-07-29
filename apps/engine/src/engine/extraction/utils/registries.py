"""Defines registry classes for shared resources."""

import re
import unicodedata


def normalize_contributor_name(name: str) -> str:
    """Normalize contributor name: remove diacritics, lowercase, strip, collapse spaces."""
    name = unicodedata.normalize("NFKD", name)
    name = "".join([c for c in name if not unicodedata.combining(c)])
    name = name.lower().strip()
    name = re.sub(r"\s+", " ", name)
    return name


def normalize_email(email: str) -> str:
    return email.lower().strip()


class ContributorRegistry:
    """
    Registry for managing contributor URIs and related data, deduplicated by normalized name.
    Aggregates all emails seen for a name.
    """

    def __init__(self):
        self._contributors = {}  # normalized_name -> URI
        self._emails = {}  # normalized_name -> set of emails

    def get_or_create_contributor_uri(self, name: str, email: str = "") -> str:
        norm_name = normalize_contributor_name(name)
        norm_email = normalize_email(email)
        if norm_name in self._contributors:
            if norm_email:
                self._emails[norm_name].add(norm_email)
            return self._contributors[norm_name]
        # Deterministic URI for this contributor
        from engine.core.namespaces import WDO

        uri = WDO[f"person/{norm_name.replace(' ', '_')}"]
        self._contributors[norm_name] = uri
        self._emails[norm_name] = set()
        if norm_email:
            self._emails[norm_name].add(norm_email)
        return uri

    def get_emails_for_contributor(self, name: str) -> set:
        norm_name = normalize_contributor_name(name)
        return self._emails.get(norm_name, set())


class FrameworkRegistry:
    """
    Registry for managing framework URIs and related data.
    """

    def __init__(self):
        self._frameworks = {}  # name -> URI
        self._counter = 0

    def get_or_create_framework_uri(self, name: str) -> str:
        """
        Returns the URI for the given framework, creating it if necessary.

        Args:
            name (str): Framework name.

        Returns:
            str: The framework's URI.
        """
        if name in self._frameworks:
            return self._frameworks[name]

        from engine.core.namespaces import WDO

        uri = WDO[f"framework/{name.replace(' ', '_')}_{self._counter}"]
        self._frameworks[name] = uri
        self._counter += 1
        return uri


class SoftwarePackageRegistry:
    """
    Registry for managing software package URIs and related data.
    """

    def __init__(self):
        self._packages = {}  # name -> URI
        self._counter = 0

    def get_or_create_package_uri(self, name: str) -> str:
        """
        Returns the URI for the given software package, creating it if necessary.

        Args:
            name (str): Package name.

        Returns:
            str: The package's URI.
        """
        if name in self._packages:
            return self._packages[name]

        from engine.core.namespaces import WDO

        uri = WDO[f"package/{name.replace(' ', '_')}_{self._counter}"]
        self._packages[name] = uri
        self._counter += 1
        return uri


class ContentRegistry:
    """
    Registry for managing content URIs and related data.
    """

    def __init__(self):
        self._contents = {}  # (repo_enc, path_enc) -> URI
        self._counter = 0

    def get_or_create_content_uri(self, repo_enc: str, path_enc: str) -> str:
        """
        Returns the URI for the given content, creating it if necessary.

        Args:
            repo_enc (str): Encoded repository name.
            path_enc (str): Encoded file path.

        Returns:
            str: The content's URI.
        """
        content_key = f"content/{repo_enc}/{path_enc}"
        if content_key in self._contents:
            return self._contents[content_key]

        from engine.core.namespaces import WDO

        uri = WDO[content_key]
        self._contents[content_key] = uri
        self._counter += 1
        return uri
