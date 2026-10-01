"""
Simulated infrastructure/diagnostic tools for the technical support agent

"""

from langchain_core.tools import tool


@tool
def check_app_status() -> str:

    """check the overall runtime status of the application: process state, 
    up time, CPU usage, memory usage and active request count.

    When to use:
    - The user report something broad or vague, example "the app is slow", 
    "is everything okay", "the app crashed".
    - As a cheap first check before drilling into logs or dependences.

    When not to use:
    - Single-user issues like a failed login or a password reset -- those don't depend on overall app health.
    - The user has already given you a specific error  (e.g. HTTP 500) -- prefer 
    check_api_health or check_server_logs for that instead.
    """

    return """
    Application Status
    ------------------
    Status: RUNNING
    Uptime: 6 hours 42 minutes
    CPU usage: 42%
    Memory usage: 68%
    Active requests: 183
    Application health check: PASS
    
    No application crash has been detected.
    """


@tool
def check_server_logs(service: str) -> str:
    """
    Inspect the most recent server log lines of one service for concrete
    error messages, and warnings.

    When to use:
    - The user reports a specific error (e.g. "HTTP 500", "it crashes
    when I submit the form").
    - After check_app_status or check_api_health indicates a
    problem, to find the underlying cause.
    - A login problem where the runbook says to check authentication
    logs -- use service="auth".

    When NOT to use:
    - Simple how-to or account questions (e.g. "how do I reset my
    password") that don't involve an application error.

    Args:
        service: Which service's logs to read: "orders" (order/API
            requests) or "auth" (login and authentication).
    """

    if "auth" in service.lower() or "login" in service.lower():
        return """
    Recent Auth Service Logs
    ------------------------
    09:12:47 INFO  Login attempt: user=jane.doe@example.com
    09:12:47 WARN  Authentication failed: invalid password
    09:13:05 WARN  Authentication failed: invalid password
    09:13:22 WARN  Authentication failed: invalid password
    09:13:40 WARN  Authentication failed: invalid password
    09:13:58 WARN  Authentication failed: invalid password
    09:13:58 WARN  Account locked after 5 failed attempts:
                user=jane.doe@example.com (auto-unlock in 30 minutes)

    Auth service is healthy; failures are due to invalid credentials.
    """

    return """
    Recent Orders Service Logs
    --------------------------
    12:41:03 INFO  Request received: POST /api/orders
    12:41:03 INFO  Authenticating request
    12:41:04 ERROR Database connection timeout
    12:41:04 ERROR psycopg2.OperationalError:
                connection to database timed out
    12:41:04 ERROR Failed to execute query
    12:41:04 ERROR HTTP 500 returned for /api/orders
    
    Repeated database timeout errors were detected.
    """


@tool
def check_db_status() -> str:
    """
    Check the primary database's health: connection status, connection
    pool utilization, and average query/connection latency.
 
    When to use:
    - Logs or symptoms point at the database specifically (timeouts,
    connection errors, "pool exhausted"-style messages).
    - An API error looks like it originates from a slow/blocked
    downstream dependency rather than the API code itself.
 
    When NOT to use:
    - Front-end-only issues, or account/login/password questions where
    nothing suggests the database is involved.
    - As a routine first check "just in case" -- only call this once
    something else has actually implicated the database.

    """  

    return """
    Database Status
    ---------------
    Status: DEGRADED
    
    Connection pool:
        Maximum connections: 100
        Active connections: 98
        Available connections: 2
    
    Average connection latency: 4.8 seconds
    Normal connection latency: < 100 ms
    
    Database health check: WARNING
    
    The database is experiencing connection saturation.
    """


@tool
def check_api_health() -> str:
    """
    Ping the primary API endpoint and report its HTTP status code and
    response time, to confirm whether an API-level error is currently
    reproducible.
 
    When to use:
    - The user reports an API error such as HTTP 500/502/503, or that
    API calls are slow or timing out.
 
    When NOT to use:
    - Issues that are clearly not API-related, e.g. a Docker container
    restarting or a static website being unreachable -- use a more
    specific tool for those instead.
    """
 
    return """
    API Health
    ----------
    Endpoint: /api/orders
    HTTP status: 500
    Response time: 5.2 seconds
    
    Expected:
    HTTP status: 200
    Response time: < 500 ms
    
    API health check: FAIL
    """

@tool
def search_internal_docs(query: str) -> str:
    """
    Search the simulated internal knowledge base / runbooks for
    troubleshooting guidance on a topic.
 
    When to use:
    - You already have a likely root cause and want the documented fix
      / recommended remediation steps for it (e.g. query="database" or
      query="500").
    - The question is a simple how-to that doesn't need any
      infrastructure inspection at all (e.g. query="password reset").
      In that case this may be the ONLY tool you need to call.
 
    Args:
        query: A short topic or keyword describing what to look up,
            e.g. "database connection issues", "HTTP 500", "login
            failure", "docker container restarting".
    """
 
    documents = {
    "database": """
    Internal Documentation: Database Connection Issues
    
    If API requests return HTTP 500 together with database timeout
    errors, check database connection pool saturation.
    
    Recommended actions:
    1. Check active database connections.
    2. Check for long-running queries.
    3. Check application connection-pool configuration.
    4. Restart affected application instances only if necessary.
    5. Escalate to the database team if saturation persists.
    """,

    "500": """
    Internal Documentation: HTTP 500 Errors
    
    HTTP 500 errors indicate that the server encountered an
    unexpected condition.
    
    Recommended investigation:
    1. Check API health.
    2. Inspect application logs.
    3. Check dependent services such as databases.
    4. Identify the underlying exception.
    5. Apply the documented remediation.
    """,

    "slow": """
    Internal Documentation: Slow Application
    
    For slow applications:
    1. Check application CPU and memory.
    2. Inspect server logs.
    3. Check database latency.
    4. Check API response times.
    5. Identify slow downstream dependencies.
    """,

    "login": """
    Internal Documentation: Login Problems
    
    For login failures:
    1. Verify authentication service status.
    2. Check authentication-related logs.
    3. Verify credentials/session configuration.
    4. Check identity provider connectivity.
    
    Database health checks are not normally required unless
    logs indicate a database dependency.
    """,

    "docker": """
    Internal Documentation: Docker Container Restarting
    
    For restarting containers:
    1. Check container status.
    2. Inspect container logs.
    3. Check memory limits.
    4. Check application startup errors.
    5. Check container health-check configuration.
    """,
    }

    query_lower = query.lower()

    if "database" in query_lower or "db" in query_lower:
        return documents["database"]

    if "500" in query_lower or "internal server" in query_lower:
        return documents["500"]

    if "slow" in query_lower or "performance" in query_lower:
        return documents["slow"]

    if "login" in query_lower or "password" in query_lower:
        return documents["login"]

    if "docker" in query_lower or "container" in query_lower:
        return documents["docker"]

    return """
    No exact internal documentation article was found.

    General guidance:
    - Inspect application logs.
    - Check relevant dependent services.
    - Verify application health.
    - Escalate if the root cause cannot be identified.

    """

### Tool collcction

tools = [check_app_status,
        check_server_logs,
        check_db_status,
        check_api_health,
        search_internal_docs,
]

tools_by_name = {t.name: t for t in tools}
    


  


    
