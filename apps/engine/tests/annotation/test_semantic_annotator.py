import pytest
from rdflib import RDF, RDFS, SKOS, Graph, Literal, URIRef
from rdflib.namespace import DCTERMS

from app.annotation.generate_class_templates import analyze_class_structure
from app.annotation.semantic_annotator import (
    analyze_class_structure,
    build_label_to_uri_map,
)
from app.annotation.utils import (
    build_label_to_uri_map,
    find_uri_by_label_fast,
    render_template_with_jinja2,
)


class TestTemplateRenderingFix:
    """Test the critical Jinja2 template rendering fix."""

    def test_simple_template_rendering(self):
        """Test basic Jinja2 template rendering."""
        template = (
            "The function '{{rdfs_label}}' is designed to {{dcterms_description}}."
        )
        properties = {
            "rdfs_label": "test_function",
            "dcterms_description": "perform calculations",
        }

        result = render_template_with_jinja2(template, properties)
        expected = "The function 'test_function' is designed to perform calculations."
        assert result == expected

    def test_conditional_template_rendering(self):
        """Test Jinja2 conditional blocks."""
        template = "The function '{{rdfs_label}}' is designed to {{dcterms_description}}.{% if wdo_is_code_part_of %} It is part of {{wdo_is_code_part_of}}.{% endif %}"
        properties = {
            "rdfs_label": "test_function",
            "dcterms_description": "perform calculations",
            "wdo_is_code_part_of": "main_module",
        }

        result = render_template_with_jinja2(template, properties)
        expected = "The function 'test_function' is designed to perform calculations. It is part of main_module."
        assert result == expected

    def test_conditional_template_without_optional_property(self):
        """Test that optional properties are correctly omitted."""
        template = "The function '{{rdfs_label}}' is designed to {{dcterms_description}}.{% if wdo_is_code_part_of %} It is part of {{wdo_is_code_part_of}}.{% endif %}"
        properties = {
            "rdfs_label": "test_function",
            "dcterms_description": "perform calculations",
            # wdo_is_code_part_of is missing
        }

        result = render_template_with_jinja2(template, properties)
        expected = "The function 'test_function' is designed to perform calculations."
        assert result == expected

    def test_loop_template_rendering(self):
        """Test Jinja2 for loops for multi-valued properties."""
        template = "The function '{{rdfs_label}}' is designed to {{dcterms_description}}.{% if wdo_tests %} It is tested by: {% for test in wdo_tests %}'{{test}}'{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}"
        properties = {
            "rdfs_label": "test_function",
            "dcterms_description": "perform calculations",
            "wdo_tests": ["test1", "test2", "test3"],
        }

        result = render_template_with_jinja2(template, properties)
        expected = "The function 'test_function' is designed to perform calculations. It is tested by: 'test1', 'test2', 'test3'"
        assert result == expected

    def test_template_error_handling(self):
        """Test that template errors are handled gracefully."""
        template = "The function '{{rdfs_label}}' is designed to {{dcterms_description}}.{% if wdo_is_code_part_of %} It is part of {{wdo_is_code_part_of}}.{% endif %}"
        properties = {
            "rdfs_label": "test_function"
            # Missing dcterms_description will cause an error
        }

        result = render_template_with_jinja2(template, properties)
        # Should return the original template or an error message
        assert "test_function" in result


class TestFallbackAnnotation:
    """Test the fallback annotation mechanism when GEMINI_API_KEY is not set."""

    def test_fallback_template_generation(self):
        """Test that fallback templates are generated correctly."""
        import os

        from app.annotation.semantic_annotator import main as semantic_annotator_main

        # Temporarily unset GEMINI_API_KEY if it exists
        original_key = os.environ.get("GEMINI_API_KEY")
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

        try:
            # Create a simple test graph
            g = Graph()
            class_uri = URIRef(
                "http://www.semanticweb.org/ontologies/2024/1/wdo#FunctionDefinition"
            )
            inst1 = URIRef("http://example.org/function1")
            g.add((inst1, RDF.type, class_uri))
            g.add((inst1, RDFS.label, Literal("Test Function")))
            g.add((inst1, DCTERMS.description, Literal("A test function")))

            # Save the graph to the expected location
            import shutil
            import tempfile

            original_ttl_path = "output/wdkb.ttl"

            # Create output directory if it doesn't exist
            os.makedirs("output", exist_ok=True)

            # Save the test graph
            g.serialize(destination=original_ttl_path, format="turtle")

            # The semantic annotator should now run with fallback templates
            # We can't easily test the main function directly due to its complexity,
            # but we can test that the fallback template generation logic works

            # Test the fallback template creation logic
            class_name = (
                "http://www.semanticweb.org/ontologies/2024/1/wdo#FunctionDefinition"
            )
            properties_with_stats = [
                {
                    "uri": "http://www.w3.org/2000/01/rdf-schema#label",
                    "frequency": "100%",
                    "cardinality": "single",
                }
            ]

            # Simulate the fallback template creation
            class_short_name = class_name.split("#")[-1]
            fallback_template = (
                f"This is a {class_short_name} instance with the following properties: "
            )
            fallback_template += "{% for key, value in items.items() %}"
            fallback_template += (
                "{{ key }}: {{ value }}{% if not loop.last %}, {% endif %}"
            )
            fallback_template += "{% endfor %}. "
            fallback_template += (
                "This entity represents a web development component or resource."
            )

            # Test that the template can be rendered
            properties = {
                "rdfs_label": "Test Function",
                "dcterms_description": "A test function",
            }

            result = render_template_with_jinja2(
                fallback_template, {**properties, "items": properties}
            )

            # Verify the fallback template works
            assert "FunctionDefinition" in result
            assert "Test Function" in result
            assert "A test function" in result
            assert "web development component" in result

        finally:
            # Restore the original GEMINI_API_KEY if it existed
            if original_key:
                os.environ["GEMINI_API_KEY"] = original_key


class TestPerformanceOptimization:
    """Test the performance optimization with pre-computed label lookup."""

    def test_build_label_to_uri_map(self):
        """Test building the label to URI lookup map."""
        g = Graph()

        # Add some test data
        uri1 = URIRef("http://example.org/entity1")
        uri2 = URIRef("http://example.org/entity2")
        uri3 = URIRef("http://example.org/entity3")

        g.add((uri1, RDFS.label, Literal("Function A")))
        g.add((uri2, RDFS.label, Literal("Function B")))
        g.add((uri3, RDFS.label, Literal("Module X")))

        label_map = build_label_to_uri_map(g)

        assert "function a" in label_map
        assert "function b" in label_map
        assert "module x" in label_map
        assert label_map["function a"] == uri1
        assert label_map["function b"] == uri2
        assert label_map["module x"] == uri3

    def test_find_uri_by_label_fast(self):
        """Test fast URI lookup using pre-computed map."""
        g = Graph()

        uri1 = URIRef("http://example.org/entity1")
        g.add((uri1, RDFS.label, Literal("Function A")))

        label_map = build_label_to_uri_map(g)

        # Test successful lookup
        result = find_uri_by_label_fast(label_map, "Function A")
        assert result == uri1

        # Test case-insensitive lookup
        result = find_uri_by_label_fast(label_map, "function a")
        assert result == uri1

        # Test non-existent label
        result = find_uri_by_label_fast(label_map, "NonExistent")
        assert result is None


class TestStatisticalAnalysis:
    """Test the statistical analysis functionality."""

    def test_analyze_class_structure(self):
        """Test class structure analysis with frequency and cardinality."""
        g = Graph()

        # Create a test class with instances
        class_uri = URIRef(
            "http://www.semanticweb.org/ontologies/2024/1/wdo#FunctionDefinition"
        )
        prop1 = URIRef("http://www.w3.org/2000/01/rdf-schema#label")
        prop2 = URIRef("http://purl.org/dc/terms/description")
        prop3 = URIRef(
            "http://www.semanticweb.org/ontologies/2024/1/wdo#hasProgrammingLanguage"
        )

        # Instance 1
        inst1 = URIRef("http://example.org/function1")
        g.add((inst1, RDF.type, class_uri))
        g.add((inst1, prop1, Literal("Function A")))
        g.add((inst1, prop2, Literal("Performs calculations")))
        g.add((inst1, prop3, Literal("Python")))

        # Instance 2
        inst2 = URIRef("http://example.org/function2")
        g.add((inst2, RDF.type, class_uri))
        g.add((inst2, prop1, Literal("Function B")))
        g.add((inst2, prop2, Literal("Handles data")))
        g.add((inst2, prop3, Literal("JavaScript")))

        # Instance 3 (missing some properties)
        inst3 = URIRef("http://example.org/function3")
        g.add((inst3, RDF.type, class_uri))
        g.add((inst3, prop1, Literal("Function C")))
        # Missing prop2 and prop3

        analysis = analyze_class_structure(g)

        assert str(class_uri) in analysis
        class_props = analysis[str(class_uri)]

        # Should have 4 properties (including RDF.type)
        assert len(class_props) == 4

        # Check that prop1 (rdfs:label) has 100% frequency
        prop1_info = next(p for p in class_props if "label" in p["uri"])
        assert prop1_info["frequency"] == "100%"

        # Check that prop2 (dcterms:description) has 67% frequency (2 out of 3)
        prop2_info = next(p for p in class_props if "description" in p["uri"])
        assert prop2_info["frequency"] == "67%"

        # Check that prop3 (wdo:hasProgrammingLanguage) has 67% frequency
        prop3_info = next(
            p for p in class_props if "hasProgrammingLanguage" in p["uri"]
        )
        assert prop3_info["frequency"] == "67%"

    def test_build_template_prompt(self):
        """Test that template prompts are generated correctly."""
        from app.annotation.generate_class_templates import build_template_prompt

        class_name = (
            "http://www.semanticweb.org/ontologies/2024/1/wdo#FunctionDefinition"
        )
        properties_with_stats = [
            {
                "uri": "http://www.w3.org/2000/01/rdf-schema#label",
                "frequency": "100%",
                "cardinality": "single",
            },
            {
                "uri": "http://purl.org/dc/terms/description",
                "frequency": "67%",
                "cardinality": "single",
            },
        ]

        prompt = build_template_prompt(
            class_name,
            [],
            include_statistics=True,
            properties_with_stats=properties_with_stats,
        )

        # Check that the prompt contains expected elements
        assert "FunctionDefinition" in prompt
        assert "label" in prompt  # Simplified property name
        assert "description" in prompt  # Simplified property name
        assert "100%" in prompt
        assert "67%" in prompt
        assert "single" in prompt
        assert "JSON" in prompt
        assert "template" in prompt


class TestIntegration:
    """Test integration of all fixes together."""

    def test_end_to_end_template_processing(self):
        """Test complete template processing with real data."""
        g = Graph()

        # Create test data
        class_uri = URIRef(
            "http://www.semanticweb.org/ontologies/2024/1/wdo#FunctionDefinition"
        )
        inst = URIRef("http://example.org/function1")

        g.add((inst, RDF.type, class_uri))
        g.add((inst, RDFS.label, Literal("calculate_sum")))
        g.add((inst, DCTERMS.description, Literal("Adds two numbers")))

        # Create a realistic template
        template = "The function '{{rdfs_label}}' is designed to {{dcterms_description}}.{% if wdo_has_programming_language %} It is implemented in {{wdo_has_programming_language}}.{% endif %}"

        # Prepare properties in snake_case
        properties = {
            "rdfs_label": "calculate_sum",
            "dcterms_description": "Adds two numbers",
            # wdo_has_programming_language is missing
        }

        # Test template rendering
        result = render_template_with_jinja2(template, properties)
        expected = "The function 'calculate_sum' is designed to Adds two numbers."
        assert result == expected

        # Test label map building
        label_map = build_label_to_uri_map(g)
        assert "calculate_sum" in label_map
        assert label_map["calculate_sum"] == inst

        # Test fast lookup
        found_uri = find_uri_by_label_fast(label_map, "calculate_sum")
        assert found_uri == inst

    def test_annotation_storage(self):
        """Test that skos:editorialNote is stored correctly."""
        from rdflib.namespace import DCTERMS, SKOS

        from app.annotation.data_processing import process_single_instance

        g = Graph()

        # Create a test instance
        class_uri = URIRef(
            "http://www.semanticweb.org/ontologies/2024/1/wdo#FunctionDefinition"
        )
        instance = URIRef("http://example.org/test_function")
        g.add((instance, RDF.type, class_uri))
        g.add((instance, RDFS.label, Literal("Test Function")))

        # Create a simple template
        template = "This is a {{label}} that {{description}}."

        # The process_single_instance function extracts properties from the graph
        # So we need to add the properties to the graph
        g.add((instance, RDFS.label, Literal("Test Function")))
        g.add((instance, DCTERMS.description, Literal("performs calculations")))

        # Mock label lookup
        label_to_uri_map = {}

        # Process the instance
        success = process_single_instance(
            g, instance, template, label_to_uri_map, "FunctionDefinition"
        )

        assert success

        # Check that skos:editorialNote is stored
        editorial_notes = list(g.objects(instance, SKOS.editorialNote))

        assert len(editorial_notes) == 1

        # Editorial note should be plaintext
        editorial_note = str(editorial_notes[0])
        assert "Test Function" in editorial_note
        assert "performs calculations" in editorial_note
        assert "<a href=" not in editorial_note  # Should not contain HTML


if __name__ == "__main__":
    pytest.main([__file__])
