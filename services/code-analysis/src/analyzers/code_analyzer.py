import ast
import re
import json
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class CodeAnalyzer:
    """Code analysis utilities for different programming languages"""
    
    def __init__(self):
        self.language_extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.cs': 'csharp',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.tf': 'terraform',
            '.hcl': 'hcl'
        }
        
        self.framework_patterns = {
            'python': {
                'django': [r'from django', r'import django', r'Django'],
                'flask': [r'from flask', r'import flask', r'Flask'],
                'fastapi': [r'from fastapi', r'import fastapi', r'FastAPI'],
                'tornado': [r'import tornado', r'tornado\.'],
                'pyramid': [r'from pyramid', r'import pyramid']
            },
            'javascript': {
                'express': [r'require\([\'"]express[\'"]', r'from [\'"]express[\'"]', r'express\(\)'],
                'react': [r'import.*React', r'from [\'"]react[\'"]', r'React\.'],
                'vue': [r'import.*Vue', r'from [\'"]vue[\'"]', r'Vue\.'],
                'angular': [r'@angular', r'import.*@angular', r'Angular'],
                'nextjs': [r'next/', r'from [\'"]next[\'"]'],
                'nuxt': [r'nuxt', r'from [\'"]nuxt[\'"]']
            },
            'java': {
                'spring': [r'@SpringBootApplication', r'org\.springframework', r'Spring'],
                'hibernate': [r'org\.hibernate', r'@Entity', r'Hibernate'],
                'struts': [r'org\.apache\.struts', r'Struts'],
                'jersey': [r'javax\.ws\.rs', r'Jersey']
            }
        }
    
    def detect_language(self, filename: str) -> str:
        """Detect programming language from filename"""
        for ext, lang in self.language_extensions.items():
            if filename.lower().endswith(ext):
                return lang
        return 'unknown'
    
    def detect_framework(self, code: str, language: str) -> Optional[str]:
        """Detect framework used in the code"""
        if language not in self.framework_patterns:
            return None
        
        frameworks = self.framework_patterns[language]
        for framework, patterns in frameworks.items():
            for pattern in patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    return framework
        
        return None
    
    async def parse_code(self, code: str, language: str) -> Dict[str, Any]:
        """Parse code structure based on language"""
        try:
            if language == 'python':
                return self._parse_python(code)
            elif language in ['javascript', 'typescript']:
                return self._parse_javascript(code)
            elif language == 'java':
                return self._parse_java(code)
            else:
                return self._parse_generic(code)
        except Exception as e:
            logger.error(f"Code parsing error for {language}: {e}")
            return {"error": str(e), "functions": [], "classes": [], "imports": []}
    
    def _parse_python(self, code: str) -> Dict[str, Any]:
        """Parse Python code using AST"""
        try:
            tree = ast.parse(code)
            
            functions = []
            classes = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args],
                        "decorators": [d.id if hasattr(d, 'id') else str(d) for d in node.decorator_list]
                    })
                
                elif isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "bases": [base.id if hasattr(base, 'id') else str(base) for base in node.bases],
                        "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    })
                
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            return {
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "total_lines": len(code.split('\n'))
            }
        
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}", "functions": [], "classes": [], "imports": []}
    
    def _parse_javascript(self, code: str) -> Dict[str, Any]:
        """Parse JavaScript/TypeScript code using regex patterns"""
        functions = []
        classes = []
        imports = []
        
        # Function patterns
        func_patterns = [
            r'function\s+(\w+)\s*\(',
            r'const\s+(\w+)\s*=\s*\(',
            r'let\s+(\w+)\s*=\s*\(',
            r'var\s+(\w+)\s*=\s*function',
            r'(\w+)\s*:\s*function',
            r'(\w+)\s*=>\s*'
        ]
        
        for pattern in func_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                functions.append({
                    "name": match.group(1),
                    "line": code[:match.start()].count('\n') + 1
                })
        
        # Class patterns
        class_matches = re.finditer(r'class\s+(\w+)', code)
        for match in class_matches:
            classes.append({
                "name": match.group(1),
                "line": code[:match.start()].count('\n') + 1
            })
        
        # Import patterns
        import_patterns = [
            r'import.*from\s+[\'"]([^\'"]+)[\'"]',
            r'require\([\'"]([^\'"]+)[\'"]\)',
            r'import\s+[\'"]([^\'"]+)[\'"]'
        ]
        
        for pattern in import_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                imports.append(match.group(1))
        
        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "total_lines": len(code.split('\n'))
        }
    
    def _parse_java(self, code: str) -> Dict[str, Any]:
        """Parse Java code using regex patterns"""
        functions = []
        classes = []
        imports = []
        
        # Method patterns
        method_matches = re.finditer(r'(public|private|protected)?\s*(static)?\s*\w+\s+(\w+)\s*\(', code)
        for match in method_matches:
            functions.append({
                "name": match.group(3),
                "line": code[:match.start()].count('\n') + 1,
                "visibility": match.group(1) or "package"
            })
        
        # Class patterns
        class_matches = re.finditer(r'(public|private)?\s*class\s+(\w+)', code)
        for match in class_matches:
            classes.append({
                "name": match.group(2),
                "line": code[:match.start()].count('\n') + 1,
                "visibility": match.group(1) or "package"
            })
        
        # Import patterns
        import_matches = re.finditer(r'import\s+([\w\.]+);', code)
        for match in import_matches:
            imports.append(match.group(1))
        
        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "total_lines": len(code.split('\n'))
        }
    
    def _parse_generic(self, code: str) -> Dict[str, Any]:
        """Generic code parsing for unsupported languages"""
        return {
            "functions": [],
            "classes": [],
            "imports": [],
            "total_lines": len(code.split('\n')),
            "language": "unsupported"
        }
    
    def extract_dependencies(self, code: str, language: str) -> List[str]:
        """Extract dependencies from code"""
        dependencies = []
        
        if language == 'python':
            # Look for requirements in imports
            import_matches = re.findall(r'(?:from|import)\s+([\w\.]+)', code)
            # Filter out standard library modules
            stdlib_modules = {'os', 'sys', 'json', 'datetime', 're', 'math', 'random'}
            dependencies = [imp.split('.')[0] for imp in import_matches if imp.split('.')[0] not in stdlib_modules]
        
        elif language in ['javascript', 'typescript']:
            # Look for npm packages
            import_matches = re.findall(r'(?:require\([\'"]|from\s+[\'"])([^\'"]+)', code)
            # Filter out relative imports
            dependencies = [imp for imp in import_matches if not imp.startswith('.') and not imp.startswith('/')]
        
        elif language == 'java':
            # Look for Maven/Gradle dependencies in imports
            import_matches = re.findall(r'import\s+([\w\.]+);', code)
            # Filter out java.* packages
            dependencies = [imp for imp in import_matches if not imp.startswith('java.')]
        
        return list(set(dependencies))  # Remove duplicates
    
    def calculate_complexity(self, code: str, language: str) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity
        
        # Count decision points
        decision_keywords = ['if', 'elif', 'else', 'for', 'while', 'try', 'except', 'case', 'switch']
        
        for keyword in decision_keywords:
            complexity += len(re.findall(rf'\b{keyword}\b', code, re.IGNORECASE))
        
        return complexity
    
    def identify_patterns(self, code: str, language: str) -> List[str]:
        """Identify common design patterns in code"""
        patterns = []
        
        # Singleton pattern
        if re.search(r'class.*Singleton|__new__.*cls\._instance', code):
            patterns.append('singleton')
        
        # Factory pattern
        if re.search(r'class.*Factory|def create_', code):
            patterns.append('factory')
        
        # Observer pattern
        if re.search(r'subscribe|notify|observer', code, re.IGNORECASE):
            patterns.append('observer')
        
        # MVC pattern
        if re.search(r'class.*Controller|class.*Model|class.*View', code):
            patterns.append('mvc')
        
        # Repository pattern
        if re.search(r'class.*Repository|def find_|def save_', code):
            patterns.append('repository')
        
        return patterns