from engine.api.db import db_connector
from engine.api.utils.sparql_loader import load_query

def get_code_complexity():
    """
    Get code complexity metrics for the codebase.
    Returns:
        dict: Complexity analysis.
    """
    # File-level complexity
    file_query = load_query('complexity/file_complexity.rq')
    file_result = db_connector.execute_sparql_query(file_query)
    files = []
    total_complexity = 0.0
    file_count = 0
    for binding in file_result.get('results', {}).get('bindings', []):
        file_name = binding.get('fileName', {}).get('value', 'Unknown')
        total_complexity_val = float(binding.get('totalComplexity', {}).get('value', 0))
        avg_complexity_val = float(binding.get('avgComplexity', {}).get('value', 0))
        function_count = int(binding.get('functionCount', {}).get('value', 0))
        line_count = int(binding.get('lineCount', {}).get('value', 0))
        token_count = int(binding.get('tokenCount', {}).get('value', 0))
        files.append({
            'file': file_name,
            'complexity': total_complexity_val,
            'avgComplexity': avg_complexity_val,
            'lines': line_count,
            'functions': function_count,
            'tokens': token_count,
        })
        total_complexity += total_complexity_val
        file_count += 1
    # Overall average complexity
    overall_query = load_query('complexity/overall_complexity.rq')
    overall_result = db_connector.execute_sparql_query(overall_query)
    overall_avg = 0.0
    total_functions = 0
    if overall_result.get('results', {}).get('bindings', []):
        b = overall_result['results']['bindings'][0]
        avg_val = b.get('avgComplexity', {}).get('value', '0')
        if avg_val != 'NaN':
            overall_avg = round(float(avg_val), 2)
        total_functions = int(b.get('totalFunctions', {}).get('value', 0))
    # Complexity distribution
    dist_query = load_query('complexity/complexity_distribution.rq')
    dist_result = db_connector.execute_sparql_query(dist_query)
    complexity_distribution = []
    for binding in dist_result.get('results', {}).get('bindings', []):
        complexity_distribution.append({
            'range': binding['complexityRange']['value'],
            'count': int(binding['count']['value']),
        })
    avg_complexity = total_complexity / file_count if file_count > 0 else 0
    high_complexity_files = len([f for f in files if f['complexity'] > 10])
    return {
        'averageComplexity': round(avg_complexity, 2),
        'overallAverageComplexity': overall_avg,
        'highComplexityFiles': high_complexity_files,
        'totalFiles': file_count,
        'totalFunctions': total_functions,
        'complexityDistribution': complexity_distribution,
        'files': files[:20],
    } 