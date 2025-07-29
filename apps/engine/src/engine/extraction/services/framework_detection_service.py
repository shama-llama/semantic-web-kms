"""Framework detection service for content analysis."""

import logging
import re

logger = logging.getLogger("FrameworkDetectionService")

# Framework type mapping for ontology subclass assignment
FRAMEWORK_TYPE_MAP = {
    # JavaScript frameworks
    "react": "JavaScriptFramework",
    "vue": "JavaScriptFramework",
    "angular": "JavaScriptFramework",
    "express": "JavaScriptFramework",
    "next": "JavaScriptFramework",
    "nuxt": "JavaScriptFramework",
    "gatsby": "JavaScriptFramework",
    "svelte": "JavaScriptFramework",
    "jquery": "JavaScriptFramework",
    "lodash": "JavaScriptFramework",
    "moment": "JavaScriptFramework",
    "axios": "JavaScriptFramework",
    "redux": "JavaScriptFramework",
    "mobx": "JavaScriptFramework",
    "graphql": "JavaScriptFramework",
    # CSS frameworks
    "bootstrap": "CSSFramework",
    "tailwind": "CSSFramework",
    "bulma": "CSSFramework",
    "foundation": "CSSFramework",
    "semantic": "CSSFramework",
    "uikit": "CSSFramework",
    "materialize": "CSSFramework",
    "purecss": "CSSFramework",
    "spectre": "CSSFramework",
    "milligram": "CSSFramework",
}


class FrameworkDetectionService:
    """
    Service for detecting frameworks in code files.
    """

    def extract_frameworks_from_code_file(
        self, file_path: str, file_type: str
    ) -> list[dict[str, str]]:
        """Extract frameworks from code files based on imports and patterns."""
        frameworks = []
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if file_type in ["JavaScriptCode", "TypeScriptCode"]:
                js_frameworks = [
                    "react",
                    "vue",
                    "angular",
                    "express",
                    "next",
                    "nuxt",
                    "gatsby",
                    "svelte",
                    "jquery",
                    "lodash",
                    "moment",
                    "axios",
                    "redux",
                    "mobx",
                    "graphql",
                ]
                for framework in js_frameworks:
                    import_patterns = [
                        rf"import.*['\"]{framework}['\"]",
                        rf"require\(['\"]{framework}['\"]\)",
                        rf"from ['\"]{framework}['\"]",
                        rf"import.*{framework}",
                        rf"require\(['\"]{framework}",
                    ]
                    for pattern in import_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            frameworks.append({"name": framework, "version": ""})
                            break

            elif file_type == "PythonCode":
                py_frameworks = [
                    "django",
                    "flask",
                    "fastapi",
                    "tornado",
                    "bottle",
                    "pyramid",
                    "cherrypy",
                    "numpy",
                    "pandas",
                    "matplotlib",
                    "scikit-learn",
                    "tensorflow",
                    "pytorch",
                ]
                for framework in py_frameworks:
                    import_patterns = [
                        rf"import {framework}",
                        rf"from {framework}",
                        rf"import.*{framework}",
                    ]
                    for pattern in import_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            frameworks.append({"name": framework, "version": ""})
                            break

            elif file_type == "JavaCode":
                java_frameworks = [
                    "spring",
                    "hibernate",
                    "junit",
                    "mockito",
                    "log4j",
                    "slf4j",
                    "jackson",
                    "gson",
                    "okhttp",
                    "retrofit",
                    "dagger",
                    "guice",
                ]
                for framework in java_frameworks:
                    import_patterns = [rf"import.*{framework}", rf"import {framework}"]
                    for pattern in import_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            frameworks.append({"name": framework, "version": ""})
                            break

            elif file_type == "CSharpCode":
                cs_frameworks = [
                    "asp.net",
                    "entity",
                    "nhibernate",
                    "nunit",
                    "moq",
                    "log4net",
                    "serilog",
                    "newtonsoft",
                    "system.text.json",
                    "mediatr",
                    "autofac",
                ]
                for framework in cs_frameworks:
                    import_patterns = [rf"using {framework}", rf"using.*{framework}"]
                    for pattern in import_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            frameworks.append({"name": framework, "version": ""})
                            break

        except Exception as e:
            logger.warning(f"Could not extract frameworks from {file_path}: {e}")

        return frameworks
