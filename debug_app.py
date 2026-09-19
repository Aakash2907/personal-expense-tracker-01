"""
debug_app.py  -  TEMPORARY helper: shows WHY the app fails to start on Vercel.

How to use (only while debugging):
  1. In vercel.json replace both "app.py" with "debug_app.py"
  2. Redeploy and open your Vercel URL
  3. If startup fails you will see the exact error as plain text (send it to
     Claude). If startup works, the normal website appears.
  4. When fixed, change vercel.json back to "app.py" (this page shows Python
     paths and file names, so do not leave it in production).

It uses only Python's standard library, so it works even when Flask is missing.
"""

import os
import sys
import traceback


def build_app():
    try:
        from app import app as real_app           # the normal Flask app
        return real_app
    except Exception:
        folder = os.path.dirname(os.path.abspath(__file__))
        report = ("STARTUP ERROR - the app could not start\n"
                  "=======================================\n\n"
                  + traceback.format_exc() +
                  "\nPython version : " + sys.version.split()[0] +
                  "\nProject folder : " + folder +
                  "\nFiles there    : " + ", ".join(sorted(os.listdir(folder))) +
                  "\ntemplates/     : " + (", ".join(sorted(os.listdir(os.path.join(folder, "templates"))))
                                          if os.path.isdir(os.path.join(folder, "templates")) else "MISSING") +
                  "\n")

        def error_app(environ, start_response):    # plain WSGI, no Flask needed
            body = report.encode("utf-8")
            start_response("500 Internal Server Error",
                           [("Content-Type", "text/plain; charset=utf-8"),
                            ("Content-Length", str(len(body)))])
            return [body]
        return error_app


app = build_app()
