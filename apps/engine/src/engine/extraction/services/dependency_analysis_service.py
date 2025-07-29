"""Dependency analysis service for content analysis."""

import json
import logging

logger = logging.getLogger("DependencyAnalysisService")


class DependencyAnalysisService:
    """
    Service for extracting dependencies from build files and code files.
    """

    def extract_dependencies_from_build_file(
        self, file_path: str, file_type: str
    ) -> list[dict[str, str]]:
        """Extract dependencies from build files with version information."""
        dependencies = []
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if file_type == "BuildScript" and "package.json" in file_path:
                try:
                    data = json.loads(content)
                    for deps_key in ["dependencies", "devDependencies"]:
                        if deps_key in data:
                            for dep_name, dep_version in data[deps_key].items():
                                dependencies.append({
                                    "name": dep_name,
                                    "version": str(dep_version),
                                })
                except json.JSONDecodeError:
                    pass

            elif file_type == "BuildScript" and "requirements.txt" in file_path:
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "==" in line:
                            package, version = line.split("==", 1)
                            dependencies.append({"name": package, "version": version})
                        elif ">=" in line:
                            package, version = line.split(">=", 1)
                            dependencies.append({
                                "name": package,
                                "version": f">={version}",
                            })
                        elif "<=" in line:
                            package, version = line.split("<=", 1)
                            dependencies.append({
                                "name": package,
                                "version": f"<={version}",
                            })
                        else:
                            package = (
                                line.split("==")[0]
                                .split(">=")[0]
                                .split("<=")[0]
                                .split("~=")[0]
                                .split("!=")[0]
                            )
                            if package:
                                dependencies.append({"name": package, "version": ""})

            elif file_type == "BuildScript" and "composer.json" in file_path:
                try:
                    data = json.loads(content)
                    for deps_key in ["require", "require-dev"]:
                        if deps_key in data:
                            for dep_name, dep_version in data[deps_key].items():
                                dependencies.append({
                                    "name": dep_name,
                                    "version": str(dep_version),
                                })
                except json.JSONDecodeError:
                    pass

            elif file_type == "BuildScript" and "Gemfile" in file_path:
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("gem "):
                        parts = line.split('"')
                        if len(parts) >= 2:
                            gem_name = parts[1]
                            version = ""
                            if len(parts) >= 4:
                                version = parts[3]
                            dependencies.append({"name": gem_name, "version": version})

            elif file_type == "BuildScript" and "go.mod" in file_path:
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("require "):
                        parts = line.split()
                        if len(parts) >= 3:
                            module_name = parts[1]
                            version = parts[2]
                            dependencies.append({
                                "name": module_name,
                                "version": version,
                            })

            elif file_type == "BuildScript" and "Cargo.toml" in file_path:
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("[dependencies.") or line.startswith(
                        "[dev-dependencies."
                    ):
                        if line.startswith("[dependencies."):
                            crate_name = line[13:-1]
                        else:
                            crate_name = line[17:-1]
                        dependencies.append({"name": crate_name, "version": ""})

        except Exception as e:
            logger.warning(f"Could not extract dependencies from {file_path}: {e}")

        return dependencies
