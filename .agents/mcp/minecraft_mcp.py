# ==============================================================================
# Minecraft MCP Server (v1.5.6)
# A zero-dependency JSON-RPC over stdio MCP server tailored for Minecraft/NeoForge
# modding. Provides class searching, source grepping, and AST-less method parsing.
# ==============================================================================
import os
import sys
# Python version check (sys.stdout.reconfigure requires Python 3.7+)
if sys.version_info < (3, 7):
    sys.stderr.write("Error: Python 3.7+ is required to run this MCP server (due to utf-8 stream reconfigure support).\n")
    sys.exit(1)

import json
import zipfile
import time
import re

# Project path is dynamically resolved to two levels up from the script's directory (.agents/mcp/minecraft_mcp.py)
PROJECT_PATH = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
CACHE_FILE = os.path.join(os.path.dirname(__file__), "mcp_jar_cache.json")

SAFE_PREFIXES = [
    os.path.realpath(os.path.expanduser("~/.gradle")),
    os.path.realpath(PROJECT_PATH)
]
if os.name == 'nt':
    SAFE_PREFIXES = [p.lower() for p in SAFE_PREFIXES]

def is_safe_path(path):
    """Prevents Path Traversal by ensuring the path is inside allowed folders. Handles Windows case insensitivity."""
    try:
        # If relative, anchor it to PROJECT_PATH first
        if not os.path.isabs(path):
            path = os.path.join(PROJECT_PATH, path)
        abs_path = os.path.realpath(path)
        
        if os.name == 'nt':
            abs_path = abs_path.lower()
            
        for prefix_abs in SAFE_PREFIXES:
            if abs_path == prefix_abs or abs_path.startswith(prefix_abs + os.sep):
                return True
        return False
    except Exception as e:
        sys.stderr.write(f"Path safety check failed: {e}\n")
        return False

def get_local_source_files():
    """Scans the local project workspace for Java/Kotlin files."""
    src_dir = os.path.join(PROJECT_PATH, "src")
    files = []
    if os.path.exists(src_dir):
        for root, dirs, filenames in os.walk(src_dir):
            for filename in filenames:
                if filename.endswith(".java") or filename.endswith(".kt"):
                    files.append(os.path.normpath(os.path.join(root, filename)))
    return files

GLOBAL_CLASS_PATHS = {}
GLOBAL_ARTIFACT_PATHS = {}

def get_source_jars():
    global GLOBAL_CLASS_PATHS, GLOBAL_ARTIFACT_PATHS
    build_gradle_path = os.path.join(PROJECT_PATH, "build.gradle")
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # 自适应缓存失效机制：如果项目路径改变，或 build.gradle 的修改时间新于缓存生成时间，则判定缓存失效并重扫
                cache_valid = data.get("project_path") == PROJECT_PATH
                if os.path.exists(build_gradle_path):
                    gradle_mtime = os.path.getmtime(build_gradle_path)
                    if gradle_mtime > data.get("timestamp", 0):
                        cache_valid = False
                
                if cache_valid and time.time() - data.get("timestamp", 0) < 86400:
                    GLOBAL_CLASS_PATHS = data.get("class_paths", {})
                    GLOBAL_ARTIFACT_PATHS = data.get("artifact_paths", {})
                    return data.get("jars", [])
        except Exception as e:
            sys.stderr.write(f"Cache load error: {e}\n")

    cache_dir = os.path.expanduser("~/.gradle/caches")
    jars = []
    subdirs_to_scan = [
        os.path.join(cache_dir, "modules-2", "files-2.1"),
        os.path.join(cache_dir, "neoform"),
        os.path.join(cache_dir, "forge_gradle")
    ]
    for sub in subdirs_to_scan:
        if os.path.exists(sub):
            for root, dirs, files in os.walk(sub):
                # Prune irrelevant directories to optimize os.walk performance
                dirs[:] = [d for d in dirs if d not in {
                    'transforms-1', 'transforms-2', 'transforms-3', 'transforms-4',
                    'locks', 'empty-directory-hashes', 'node-compile', 'dependency-resolution-keys',
                    'journal-1', 'transactions-3'
                } and not d.startswith('transforms-')]
                
                for file in files:
                    if file.endswith("-sources.jar") or (file.endswith(".jar") and "sources" in file.lower()):
                        jars.append(os.path.normpath(os.path.join(root, file)))
    
    # 提前抓取过滤后核心 Sources JAR 包的类文件与资源文件列表索引，控制缓存 JSON 大小
    core_jars = filter_jars(jars, scan_all_deps=False)
    class_paths = {}
    artifact_paths = {}
    for c_jar in core_jars:
        try:
            with zipfile.ZipFile(c_jar, 'r') as z:
                names = z.namelist()
                class_paths[c_jar] = [name for name in names if name.endswith((".java", ".kt"))]
                artifact_paths[c_jar] = [
                    name for name in names 
                    if not name.endswith((".java", ".kt", ".class"))
                    and not name.startswith("META-INF/")
                ]
        except Exception as e:
            sys.stderr.write(f"Failed to index files for jar {c_jar}: {e}\n")
            
    GLOBAL_CLASS_PATHS = class_paths
    GLOBAL_ARTIFACT_PATHS = artifact_paths
    
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.time(), 
                "jars": jars, 
                "class_paths": class_paths, 
                "artifact_paths": artifact_paths,
                "project_path": PROJECT_PATH
            }, f, indent=2)
    except Exception as e:
        sys.stderr.write(f"Cache save error: {e}\n")
    return jars

def filter_jars(jars, scan_all_deps=False):
    """Filters jars to prioritize Minecraft/NeoForge/Common Mods and avoid Netty/Guava bloat unless requested."""
    if scan_all_deps:
        return jars
    filtered = []
    
    # 常用模组/API 白名单特征词，用于在跨模组联调时自动放行其源码包
    mod_keywords = [
        "minecraft", "neoforge", "forge", "parchment",
        "geckolib", "curios", "patchouli", "jei", "rei", "emi",
        "architectury", "cloth-config", "citadel", "pehkui"
    ]
    
    # 必须拦截的底层臃肿依赖包特征词，防止污染搜索
    block_keywords = [
        "netty", "guava", "gson", "log4j", "slf4j", "commons-", "asm",
        "jackson", "httpclient", "jna", "lwjgl", "icu4j", "fastutil"
    ]
    
    for jar in jars:
        name = os.path.basename(jar).lower()
        if any(bk in name for bk in block_keywords):
            continue
        if any(kw in name for kw in mod_keywords):
            filtered.append(jar)
    return filtered

import threading
import traceback

initialized_event = threading.Event()

def watch_handshake():
    # 延迟 10 秒检测是否收到并处理了 initialize 握手请求
    time.sleep(10.0)
    if not initialized_event.is_set():
        try:
            mcp_dir = os.path.dirname(os.path.abspath(__file__))
            err_log = os.path.join(mcp_dir, "mcp_error.log")
            with open(err_log, "w", encoding="utf-8") as f:
                f.write("--- MCP Handshake Timeout (10s) ---\n")
                f.write(f"Python executable: {sys.executable}\n")
                f.write(f"Command line arguments: {sys.argv}\n")
                f.write("Host did not send initialize request within 10s. Please check if Host correctly configured stdio redirect.\n")
        except:
            pass

def search_class(query, scan_all_deps=False):
    results = []
    query_lower = query.lower()

    local_files = get_local_source_files()
    for lf in local_files:
        base = os.path.basename(lf).lower()
        if query_lower in base:
            results.append({
                "jar": "Local Workspace Project",
                "path": os.path.relpath(lf, PROJECT_PATH).replace('\\', '/'),
                "full_jar_path": lf.replace('\\', '/')
            })

    all_jars = get_source_jars()
    jars = filter_jars(all_jars, scan_all_deps)
    for jar in jars:
        if jar in GLOBAL_CLASS_PATHS:
            for name in GLOBAL_CLASS_PATHS[jar]:
                base = os.path.basename(name).lower()
                if query_lower in base:
                    results.append({
                        "jar": os.path.basename(jar),
                        "path": name.replace('\\', '/'),
                        "full_jar_path": jar.replace('\\', '/')
                    })
        else:
            try:
                with zipfile.ZipFile(jar, 'r') as z:
                    for name in z.namelist():
                        if name.endswith(".java") or name.endswith(".kt"):
                            base = os.path.basename(name).lower()
                            if query_lower in base:
                                results.append({
                                    "jar": os.path.basename(jar),
                                    "path": name.replace('\\', '/'),
                                    "full_jar_path": jar.replace('\\', '/')
                                })
            except Exception as e:
                sys.stderr.write(f"Failed to scan jar {jar}: {e}\n")
                continue
    return results, len(jars), len(all_jars)

def grep_source(query, max_results=50, scan_all_deps=False):
    results = []
    query_lower = query.lower()
    query_pat = re.compile(re.escape(query), re.IGNORECASE)
    
    # 使用 mutable 包装器确保多线程下数据安全计数
    class Counter:
        val = 0
    count = Counter()

    local_files = get_local_source_files()
    for lf in local_files:
        if count.val >= max_results:
            break
        try:
            with open(lf, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                if query_pat.search(content):
                    lines = content.splitlines()
                    matches = []
                    for idx, line in enumerate(lines):
                        if query_lower in line.lower():
                            matches.append({"line_num": idx + 1, "text": line.strip()})
                    
                    file_matches = matches[:5]
                    if file_matches:
                        results.append({
                            "jar": "Local Workspace Project",
                            "path": os.path.relpath(lf, PROJECT_PATH).replace('\\', '/'),
                            "full_jar_path": lf.replace('\\', '/'),
                            "matches": file_matches
                        })
                        count.val += len(file_matches)
        except Exception as e:
            sys.stderr.write(f"Failed to grep local file {lf}: {e}\n")

    def grep_in_jar(jar):
        matches_in_jar = []
        try:
            with zipfile.ZipFile(jar, 'r') as z:
                for name in z.namelist():
                    if name.endswith(".java") or name.endswith(".kt"):
                        try:
                            content = z.read(name).decode('utf-8', errors='replace')
                            if query_pat.search(content):
                                lines = content.splitlines()
                                matches = []
                                for idx, line in enumerate(lines):
                                    if query_lower in line.lower():
                                        matches.append({"line_num": idx + 1, "text": line.strip()})
                                
                                file_matches = matches[:5]
                                if file_matches:
                                    matches_in_jar.append({
                                        "jar": os.path.basename(jar),
                                        "path": name.replace('\\', '/'),
                                        "full_jar_path": jar.replace('\\', '/'),
                                        "matches": file_matches
                                    })
                        except Exception as e:
                            sys.stderr.write(f"Failed to read file {name} inside jar {jar}: {e}\n")
        except Exception as e:
            sys.stderr.write(f"Failed to open jar {jar}: {e}\n")
        return matches_in_jar

    all_jars = get_source_jars()
    jars = filter_jars(all_jars, scan_all_deps)

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(grep_in_jar, jar): jar for jar in jars}
        for future in as_completed(futures):
            if count.val >= max_results:
                for f in futures:
                    f.cancel()
                break
            try:
                jar_matches = future.result()
                for match in jar_matches:
                    if count.val >= max_results:
                        break
                    results.append(match)
                    count.val += len(match["matches"])
            except Exception as e:
                sys.stderr.write(f"Thread execution failed: {e}\n")

    return results, len(jars), len(all_jars)

def read_file(jar_path, file_path="", start_line=None, end_line=None, show_line_numbers=True):
    if not is_safe_path(jar_path):
        return "Security Error: Access denied. The specified jar/file path is outside the allowed directories."
        
    try:
        if not jar_path.lower().endswith(".jar") and os.path.exists(jar_path):
            with open(jar_path, 'r', encoding='utf-8', errors='replace') as f:
                raw_content = f.read()
        else:
            jar_path = jar_path.replace('/', os.sep)
            file_path = file_path.replace('\\', '/').lstrip('/')
            with zipfile.ZipFile(jar_path, 'r') as z:
                with z.open(file_path) as f:
                    raw_content = f.read().decode('utf-8', errors='replace')
                    
        lines = raw_content.splitlines()
        total_lines = len(lines)
        s = max(1, start_line) if start_line is not None else 1
        e = min(total_lines, end_line) if end_line is not None else total_lines
        
        sliced = lines[s-1:e]
        output_lines = []
        for idx, line in enumerate(sliced):
            current_line_num = s + idx
            if show_line_numbers:
                output_lines.append(f"{current_line_num:4d} | {line}")
            else:
                output_lines.append(line)
                
        header = f"// Sliced from Line {s} to {e} of {total_lines} total lines\n"
        return header + "\n".join(output_lines)
    except Exception as e:
        sys.stderr.write(f"Error in read_file: {str(e)}\n")
        return f"Error reading file: {str(e)}"

def strip_comments_preserve_lines(text):
    """Replaces Java comments and strings with spaces while preserving line breaks and character offsets."""
    pattern = re.compile(
        r'(/\*.*?\*/)|(//.*?(?=\n|$))|("""(?:\\.|[^"\\]|"(?!""))*""")|("(?:\\.|[^"\\])*")|(\'(?:\\.|[^\'\\])*\')',
        re.DOTALL
    )
    def replacer(match):
        return re.sub(r'[^\n]', ' ', match.group(0))

    return pattern.sub(replacer, text)

def extract_methods(cleansed_content):
    """Robust brace-tracking method parser supporting generics, constructors, and annotations.
    
    Rather than constructing a full AST parser (which is slow, fragile, and requires heavy dependencies),
    this function uses a character-by-character scan and state machine tracking to identify method declarations.
    """
    methods = []
    idx = 0
    length = len(cleansed_content)
    
    # Operators and structure indicators that should NOT appear in a method declaration prefix.
    # We include '(' to filter out nested method calls like `doSomething(bar())`.
    invalid_chars = set("=+-*/!%^&|:(")
    
    while idx < length:
        # --- STEP 1: Find the next potential method parameter list ---
        idx = cleansed_content.find('(', idx)
        if idx == -1:
            break
            
        # --- STEP 2: Find the matching closing parenthesis ---
        paren_depth = 1
        end_idx = idx + 1
        while end_idx < length and paren_depth > 0:
            if cleansed_content[end_idx] == '(':
                paren_depth += 1
            elif cleansed_content[end_idx] == ')':
                paren_depth -= 1
            end_idx += 1
            
        if paren_depth != 0:
            idx += 1
            continue
            
        # --- STEP 3: Scan ahead to confirm it's followed by a method body ({) or end of declaration (;) ---
        ahead_idx = end_idx
        is_method = False
        while ahead_idx < length:
            c = cleansed_content[ahead_idx]
            if c.isspace():
                ahead_idx += 1
            elif c in ('{', ';'):
                is_method = True
                break
            elif cleansed_content.startswith("throws", ahead_idx):
                ahead_idx += 6  # Skip Java 'throws' keyword
            elif c.isalnum() or c in (',', '.', '<', '>', '[', ']', '?'):
                # Allow types, generics, arrays, and wildcards in signature lookahead
                ahead_idx += 1
            else:
                break
                
        if not is_method:
            idx += 1
            continue
            
        # --- STEP 4: Scan backward from '(' to extract the method name ---
        back_idx = idx - 1
        while back_idx >= 0 and cleansed_content[back_idx].isspace():
            back_idx -= 1
            
        name_end = back_idx + 1
        while back_idx >= 0 and (cleansed_content[back_idx].isalnum() or cleansed_content[back_idx] == '_'):
            back_idx -= 1
        name_start = back_idx + 1
        method_name = cleansed_content[name_start:name_end]
        
        # Guard: Ignore Java keywords that use parentheses (control flow blocks)
        if not method_name or method_name in ('if', 'for', 'while', 'switch', 'catch', 'synchronized', 'return', 'try', 'new'):
            idx += 1
            continue
            
        # --- STEP 5: Find the boundary of the declaration prefix (stop at previous block end/separator) ---
        search_start = back_idx
        while search_start >= 0 and cleansed_content[search_start] not in ('{', '}', ';'):
            search_start -= 1
            
        decl_prefix = cleansed_content[search_start+1:name_start]
        
        # --- STEP 6: Filter false positives using clean prefix checks ---
        # Exclude annotation assignments from invalidating method matches (supports Level 2 nested parentheses)
        decl_prefix_clean = re.sub(r'@[A-Za-z0-9_.]+(?:\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\))?', '', decl_prefix)
        # Strip generic bounds <...> recursively to prevent intersection types (&) or wildcards from causing false exclusions
        while True:
            stripped = re.sub(r'<[^<>]*>', '', decl_prefix_clean)
            if len(stripped) == len(decl_prefix_clean):
                break
            decl_prefix_clean = stripped
            
        if any(c in decl_prefix_clean for c in invalid_chars):
            idx = ahead_idx
            continue
            
        # Ensure declaration doesn't contain forbidden keywords in its prefix
        tokens = decl_prefix.split()
        if any(kw in tokens for kw in ('new', 'return', 'throw', 'else', 'if', 'for', 'while', 'catch', 'switch', 'try', 'synchronized')):
            idx = ahead_idx
            continue
            
        # Validate declaration format (must have modifier or be in top-level scope not preceded by a dot)
        is_valid = False
        if any(mod in {'public', 'protected', 'private', 'abstract', 'default'} for mod in tokens):
            is_valid = True
        elif len(tokens) >= 1 and not decl_prefix.strip().endswith('.'):
            is_valid = True
            
        # --- STEP 7: Save clean method signature and line number ---
        if is_valid:
            sig_start = search_start + 1
            while sig_start < name_start and cleansed_content[sig_start].isspace():
                sig_start += 1
                
            sig = cleansed_content[sig_start:ahead_idx].strip()
            sig = re.sub(r'\s+', ' ', sig)  # Normalize whitespace
            
            line_num = cleansed_content[:sig_start].count('\n') + 1
            methods.append({"line_num": line_num, "signature": sig})
            
        idx = ahead_idx
        
    return methods

def extract_kotlin_methods(cleansed_content):
    """Kotlin function declaration extractor supporting multiline signatures via brace/parenthesis tracking."""
    methods = []
    length = len(cleansed_content)
    idx = 0
    
    while idx < length:
        idx = cleansed_content.find("fun", idx)
        if idx == -1:
            break
            
        # Ensure 'fun' is a standalone word (word boundary check)
        is_word = (idx == 0 or not cleansed_content[idx-1].isalnum() and cleansed_content[idx-1] != '_') and \
                  (idx + 3 >= length or not cleansed_content[idx+3].isalnum() and cleansed_content[idx+3] != '_')
                  
        if not is_word:
            idx += 3
            continue
            
        # Matches either standard space or generics: e.g. `fun foo()` or `fun<T> generic()`
        after_fun = cleansed_content[idx+3:idx+4]
        if not after_fun or (not after_fun.isspace() and after_fun != '<'):
            idx += 3
            continue
            
        # Extract starting line number
        line_num = cleansed_content[:idx].count('\n') + 1
        
        # Scan forward to find the end of the signature (stops at body { or single-expression =)
        end_idx = idx + 3
        paren_depth = 0
        sig_end = -1
        
        while end_idx < length:
            c = cleansed_content[end_idx]
            if c == '(':
                paren_depth += 1
            elif c == ')':
                paren_depth -= 1
            elif c in ('{', '=') and paren_depth == 0:
                sig_end = end_idx
                break
            elif c == ';' and paren_depth == 0:
                sig_end = end_idx
                break
            end_idx += 1
            
        if sig_end != -1:
            sig_raw = cleansed_content[idx:sig_end]
            # Normalize whitespace/newlines into a single line
            sig = ' '.join(sig_raw.split())
            if sig.startswith("}"):
                sig = sig[1:].strip()
            methods.append({
                "line_num": line_num,
                "signature": sig
            })
            idx = end_idx + 1
        else:
            idx += 3
            
    return methods

def list_methods(jar_path, class_path):
    if not is_safe_path(jar_path):
        return "Security Error: Access denied. The specified jar/file path is outside the allowed directories."
    try:
        if not jar_path.lower().endswith(".jar") and os.path.exists(jar_path):
            with open(jar_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        else:
            jar_path = jar_path.replace('/', os.sep)
            class_path = class_path.replace('\\', '/').lstrip('/')
            with zipfile.ZipFile(jar_path, 'r') as z:
                with z.open(class_path) as f:
                    content = f.read().decode('utf-8', errors='replace')
        
        is_kotlin = class_path.lower().endswith(".kt") or (not jar_path.lower().endswith(".jar") and jar_path.lower().endswith(".kt"))
        cleansed_content = strip_comments_preserve_lines(content)
        
        if is_kotlin:
            methods = extract_kotlin_methods(cleansed_content)
            output = {
                "methods": methods,
                "metadata": {
                    "language": "kotlin",
                    "tip": "Kotlin files use the 'fun' keyword for all function declarations. You can also use grep_source(query='fun ') to list or search functions across the entire project."
                }
            }
        else:
            methods = extract_methods(cleansed_content)
            output = {
                "methods": methods,
                "metadata": {
                    "language": "java"
                }
            }
            
        return json.dumps(output, indent=2, ensure_ascii=False)
    except Exception as e:
        sys.stderr.write(f"Error in list_methods: {str(e)}\n")
        return f"Error listing methods: {str(e)}"

def clear_cache():
    try:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            return "Cache cleared successfully. A re-scan will trigger on the next query."
        return "Cache was already empty."
    except Exception as e:
        sys.stderr.write(f"Error clearing cache: {str(e)}\n")
        return f"Error clearing cache: {str(e)}"

def search_artifact(query, extension=None):
    results = []
    query_lower = query.lower()
    
    # 搜索本地 resources 目录
    resources_dir = os.path.join(PROJECT_PATH, "src", "main", "resources")
    if os.path.exists(resources_dir):
        for root, dirs, files in os.walk(resources_dir):
            for file in files:
                if query_lower in file.lower():
                    if extension and not file.endswith(f".{extension}"):
                        continue
                    full_path = os.path.join(root, file)
                    results.append({
                        "jar": "Local Resources",
                        "path": os.path.relpath(full_path, PROJECT_PATH).replace('\\', '/'),
                        "full_jar_path": full_path.replace('\\', '/')
                    })
    
    # 搜索 JAR 中的资源文件
    for jar, files in GLOBAL_ARTIFACT_PATHS.items():
        for file in files:
            if query_lower in file.lower():
                if extension and not file.endswith(f".{extension}"):
                    continue
                results.append({
                    "jar": os.path.basename(jar),
                    "path": file.replace('\\', '/'),
                    "full_jar_path": jar.replace('\\', '/')
                })
    
    return results

def read_latest_crash_report():
    import glob
    # 扫描本地项目根目录下的 crash-reports 以及 run/crash-reports 子目录（开发期客户端常驻路径）
    search_paths = [
        os.path.join(PROJECT_PATH, "crash-reports"),
        os.path.join(PROJECT_PATH, "run", "crash-reports")
    ]
    
    files = []
    for path in search_paths:
        if os.path.exists(path):
            files.extend(glob.glob(os.path.join(path, "crash-*.txt")))
            
    if not files:
        return "No crash report files found in 'crash-reports/' or 'run/crash-reports/'."
        
    latest_file = max(files, key=os.path.getmtime)
    
    try:
        with open(latest_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            
        cleaned_lines = []
        capture = True
        
        # 截断与清洗：当遇到 "-- System Details --" 时截断后续无关的显卡、系统环境变量等噪音，节约 Token
        for line in content.splitlines():
            if "-- System Details --" in line:
                cleaned_lines.append("\n[... System details truncated to save tokens ...]\n")
                capture = False
            if capture:
                cleaned_lines.append(line)
                
        header = f"// Automatically extracted and cleaned from the latest crash report: {os.path.basename(latest_file)}\n"
        # 限制最大输出 250 行，保护上下文边界
        return header + "\n".join(cleaned_lines[:250])
    except Exception as e:
        sys.stderr.write(f"Error reading latest crash report: {str(e)}\n")
        return f"Error reading latest crash report: {str(e)}"

def send_response(resp):
    sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
    sys.stdout.flush()

def send_tool_response(req_id, text, is_error=False):
    resp = {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": text
                }
            ]
        }
    }
    if is_error:
        resp["result"]["isError"] = True
    send_response(resp)

def send_error(req_id, code, message):
    resp = {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": code,
            "message": message
        }
    }
    send_response(resp)

def print_mcp_onboarding():
    abs_project_path = os.path.abspath(PROJECT_PATH).replace("\\", "/")
    abs_script_path = os.path.abspath(__file__).replace("\\", "/")
    
    border = "=" * 78
    print(border)
    print(" [NeoForge 1.21.1 AI Starter] MCP Probe Onboarding Helper")
    print(border)
    print(f" Detected project path: {abs_project_path}")
    print(f" Detected script path:  {abs_script_path}")
    print(border)
    print(" Copy the JSON config snippet below to register this server in your client:")
    print("")
    print(" For Cline (.vscode/cline_mcp_settings.json) or Roo Code:")
    print("```json")
    print(json.dumps({
        "mcpServers": {
            "minecraft-mcp": {
                "command": "python",
                "args": [
                    abs_script_path
                ]
            }
        }
    }, indent=2))
    print("```")
    print("")
    print(" For Cursor (Settings -> Features -> MCP -> Add New MCP Server):")
    print("  - Name: minecraft-mcp")
    print("  - Type: command")
    print(f"  - Command: python \"{abs_script_path}\"")
    print("")
    print(" For Claude Code (Run command globally):")
    print(f"  claude mcp add minecraft-mcp python \"{abs_script_path}\"")
    print("")
    print(" For Grok Build / Other stdio MCP Clients:")
    print(f"  Register command: python \"{abs_script_path}\"")
    print(border)
    print(" INSTRUCTION: Copy and paste the corresponding block above into your AI client.")
    print(border)

def main():
    if sys.stdin.isatty() or "--help" in sys.argv or "-h" in sys.argv:
        print_mcp_onboarding()
        sys.exit(0)

    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stdin.reconfigure(encoding='utf-8', errors='replace')
    
    t = threading.Thread(target=watch_handshake, daemon=True)
    t.start()
    
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            req = json.loads(line)
        except Exception:
            continue
            
        method = req.get("method")
        req_id = req.get("id")
        
        if method == "notifications/initialized":
            sys.stderr.write("MCP connection initialized.\n")
            sys.stderr.flush()
            continue
            
        if method == "initialize":
            initialized_event.set()
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "minecraft-mcp",
                        "version": "1.5.6"
                    }
                }
            }
            send_response(resp)
        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "search_class",
                            "description": "Search for Java/Kotlin class files matching a class name in project or dependencies",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "The class name or partial name to find"
                                    },
                                    "scan_all_deps": {
                                        "type": "boolean",
                                        "description": "If true, scans all dependencies (like netty/guava). Default is false (faster, searches core minecraft/neoforge only)."
                                    }
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "grep_source",
                            "description": "Search inside all Java/Kotlin source files (project and core dependencies) for a text string. To find subclass or interface implementations, search for patterns like 'implements SuperName' or 'extends SuperName'.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "The code pattern or text string to search for"
                                    },
                                    "max_results": {
                                        "type": "integer",
                                        "description": "Limit output results to prevent output bloat (default 50)"
                                    },
                                    "scan_all_deps": {
                                        "type": "boolean",
                                        "description": "If true, scans all dependencies (like netty/guava). Default is false (faster, searches core minecraft/neoforge only)."
                                    }
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "read_file",
                            "description": "Read the source code or asset content of any file (.java, .kt, .json, .toml) with optional line numbers and ranges",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "jar_path": {
                                        "type": "string",
                                        "description": "Absolute path of the source jar file or workspace file"
                                    },
                                    "file_path": {
                                        "type": "string",
                                        "description": "Relative path of the file inside jar (omit or leave empty if reading local workspace file)"
                                    },
                                    "start_line": {
                                        "type": "integer",
                                        "description": "Optional starting line number (1-indexed)"
                                    },
                                    "end_line": {
                                        "type": "integer",
                                        "description": "Optional ending line number (1-indexed, inclusive)"
                                    },
                                    "show_line_numbers": {
                                        "type": "boolean",
                                        "description": "If true, prefixes lines with line numbers. Default is true."
                                    }
                                },
                                "required": ["jar_path"]
                            }
                        },
                        {
                            "name": "read_class",
                            "description": "Backward compatible alias for read_file. Reads the source code of a class with optional line numbers.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "jar_path": {
                                        "type": "string",
                                        "description": "Absolute path of the source jar file or workspace file"
                                    },
                                    "class_path": {
                                        "type": "string",
                                        "description": "Alias for file_path. Relative path inside jar."
                                    },
                                    "start_line": {
                                        "type": "integer",
                                        "description": "Optional starting line number (1-indexed)"
                                    },
                                    "end_line": {
                                        "type": "integer",
                                        "description": "Optional ending line number (1-indexed, inclusive)"
                                    },
                                    "show_line_numbers": {
                                        "type": "boolean",
                                        "description": "If true, prefixes lines with line numbers. Default is true."
                                    }
                                },
                                "required": ["jar_path"]
                            }
                        },
                        {
                            "name": "list_methods",
                            "description": "List all methods declared inside a class file with starting line numbers",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "jar_path": {
                                        "type": "string",
                                        "description": "Absolute path of the source jar file or workspace file"
                                    },
                                    "class_path": {
                                        "type": "string",
                                        "description": "Relative path inside jar (omit or leave empty if reading local workspace file)"
                                    }
                                },
                                "required": ["jar_path"]
                            }
                        },
                        {
                            "name": "search_artifact",
                            "description": "Search for non-code assets (JSON recipes, loot tables, blockstates, textures) inside project and dependency JARs",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Part of the file path or name to search (e.g., 'ruby_ore.json')"
                                    },
                                    "extension": {
                                        "type": "string",
                                        "description": "Optional file extension filter (e.g., 'json', 'toml', 'png')"
                                    }
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "read_latest_crash_report",
                            "description": "Locate and read the most recent Minecraft crash report from the crash-reports directory. Clean and extract only the relevant Java stacktrace, mixin errors, and loaded mods to save tokens.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "clear_cache",
                            "description": "Manually force clear the scanned source jar paths cache to index newly added dependencies",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    ]
                }
            }
            send_response(resp)
        elif method == "tools/call":
            params = req.get("params", {})
            name = params.get("name")
            arguments = params.get("arguments", {})
            
            try:
                if name == "search_class":
                    q = arguments.get("query", "")
                    if not q:
                        send_error(req_id, -32602, "Invalid parameter: query cannot be empty")
                        continue
                    if not isinstance(q, str):
                        q = str(q)
                    sad = arguments.get("scan_all_deps", False)
                    if isinstance(sad, str): sad = sad.lower() == "true"
                    res, scanned_count, total_count = search_class(q, sad)
                    output = {
                        "results": res,
                        "metadata": {
                            "scanned_jars": scanned_count,
                            "total_dependency_jars": total_count,
                            "tip": "Use scan_all_deps=true to include all dependency jars" if not sad else "Scanned all dependencies"
                        }
                    }
                    text = json.dumps(output, indent=2, ensure_ascii=False)
                    send_tool_response(req_id, text)
                elif name == "grep_source":
                    q = arguments.get("query", "")
                    if not q:
                        send_error(req_id, -32602, "Invalid parameter: query cannot be empty")
                        continue
                    if not isinstance(q, str):
                        q = str(q)
                    mr = arguments.get("max_results", 50)
                    try:
                        mr = int(mr)
                    except (ValueError, TypeError):
                        mr = 50
                    sad = arguments.get("scan_all_deps", False)
                    if isinstance(sad, str): sad = sad.lower() == "true"
                    res, scanned_count, total_count = grep_source(q, mr, sad)
                    output = {
                        "results": res,
                        "metadata": {
                            "scanned_jars": scanned_count,
                            "total_dependency_jars": total_count,
                            "tip": "Use scan_all_deps=true to include all dependency jars" if not sad else "Scanned all dependencies"
                        }
                    }
                    text = json.dumps(output, indent=2, ensure_ascii=False)
                    send_tool_response(req_id, text)
                elif name in ("read_file", "read_class"):
                    j = arguments.get("jar_path")
                    if not j:
                        send_error(req_id, -32602, "Missing required parameter: jar_path. Example usage: read_file(jar_path='D:/project/src/main/resources/pack.mcmeta') or read_file(jar_path='/path/to/some-sources.jar', file_path='data/minecraft/recipe/stone.json')")
                        continue
                        
                    # 兼容读取 class_path (alias) 或 file_path
                    f_path = arguments.get("file_path", "")
                    if name == "read_class" and not f_path:
                        f_path = arguments.get("class_path", "")
                        
                    sl = arguments.get("start_line")
                    try:
                        if sl is not None: sl = int(sl)
                    except (ValueError, TypeError):
                        send_error(req_id, -32602, f"Invalid parameter: start_line must be an integer. Provided value: {sl}. Example: start_line=1, end_line=100")
                        continue
                        
                    el = arguments.get("end_line")
                    try:
                        if el is not None: el = int(el)
                    except (ValueError, TypeError):
                        send_error(req_id, -32602, f"Invalid parameter: end_line must be an integer. Provided value: {el}. Example: start_line=1, end_line=100")
                        continue
                        
                    sln = arguments.get("show_line_numbers")
                    if sln is None: sln = True
                    if isinstance(sln, str): sln = sln.lower() == "true"
                        
                    text = read_file(str(j), str(f_path), sl, el, sln)
                    is_err = text.startswith("Security Error") or text.startswith("Error reading file")
                    send_tool_response(req_id, text, is_error=is_err)
                elif name == "list_methods":
                    j = arguments.get("jar_path")
                    c = arguments.get("class_path", "")
                    if not j:
                        send_error(req_id, -32602, "Missing required parameter: jar_path")
                        continue
                    text = list_methods(str(j), str(c))
                    is_err = text.startswith("Security Error") or text.startswith("Error listing methods")
                    send_tool_response(req_id, text, is_error=is_err)
                elif name == "search_artifact":
                    q = arguments.get("query", "")
                    if not q:
                        send_error(req_id, -32602, "Invalid parameter: query cannot be empty")
                        continue
                    if not isinstance(q, str):
                        q = str(q)
                    ext = arguments.get("extension")
                    if ext is not None:
                        ext = str(ext)
                    res = search_artifact(q, ext)
                    output = {
                        "results": res,
                        "metadata": {
                            "tip": "Use extension parameter to filter by extension (e.g. 'json')"
                        }
                    }
                    text = json.dumps(output, indent=2, ensure_ascii=False)
                    send_tool_response(req_id, text)
                elif name == "read_latest_crash_report":
                    text = read_latest_crash_report()
                    is_err = text.startswith("No crash report files found") or text.startswith("Error reading")
                    send_tool_response(req_id, text, is_error=is_err)
                elif name == "clear_cache":
                    text = clear_cache()
                    send_tool_response(req_id, text)
                elif name is None and req_id is not None:
                    send_error(req_id, -32600, "Missing required parameter: name")
                elif req_id is not None:
                    send_error(req_id, -32601, f"Tool not found: {name}")
            except Exception as e:
                send_tool_response(req_id, f"Internal error during tool execution: {str(e)}", is_error=True)
        else:
            if req_id is not None:
                send_error(req_id, -32601, f"Method not found: {method}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            mcp_dir = os.path.dirname(os.path.abspath(__file__))
            err_log = os.path.join(mcp_dir, "mcp_error.log")
            with open(err_log, "a", encoding="utf-8") as f:
                f.write("--- MCP Crash Report ---\n")
                f.write(f"Error: {e}\n")
                f.write(traceback.format_exc())
        except:
            pass
