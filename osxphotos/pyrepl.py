""" Custom Python REPL based on ptpython that allows quitting with custom keywords instead of `quit()` """

""" This file is distributed under the same license as the ptpython package:

Copyright (c) 2015, Jonathan Slenders (ptpython), (c) 2021 Rhet Turnbull (this file)

All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice, this
  list of conditions and the following disclaimer in the documentation and/or
  other materials provided with the distribution.

* Neither the name of the {organization} nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys
from typing import Callable, List, Optional

from ptpython.repl import (
    ContextManager,
    DummyContext,
    PythonRepl,
    builtins,
    patch_stdout_context,
)


class PyReplQuitter(PythonRepl):
    """Custom pypython repl that allows quitting REPL with custom commands"""

    def __init__(self, *args, quit_words: Optional[List[str]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.quit_words = quit_words or ["quit", "q"]

    def eval(self, line: str) -> object:
        if line.strip() in self.quit_words:
            sys.exit(0)
        return super().eval(line)


def embed_repl(
    globals=None,
    locals=None,
    configure: Optional[Callable[[PythonRepl], None]] = None,
    vi_mode: bool = False,
    history_filename: Optional[str] = None,
    title: Optional[str] = None,
    startup_paths=None,
    patch_stdout: bool = False,
    return_asyncio_coroutine: bool = False,
    quit_words: Optional[List[str]] = None,
) -> None:
    """
    Call this to embed  Python shell at the current point in your program.
    It's similar to `IPython.embed` and `bpython.embed`. ::
        from prompt_toolkit.contrib.repl import embed
        embed(globals(), locals())
    :param vi_mode: Boolean. Use Vi instead of Emacs key bindings.
    :param configure: Callable that will be called with the `PythonRepl` as a first
                      argument, to trigger configuration.
    :param title: Title to be displayed in the terminal titlebar. (None or string.)
    :param patch_stdout:  When true, patch `sys.stdout` so that background
        threads that are printing will print nicely above the prompt.
    """
    # Default globals/locals
    if globals is None:
        globals = {
            "__name__": "__main__",
            "__package__": None,
            "__doc__": None,
            "__builtins__": builtins,
        }

    locals = locals or globals

    def get_globals():
        return globals

    def get_locals():
        return locals

    # Create REPL.
    repl = PyReplQuitter(
        get_globals=get_globals,
        get_locals=get_locals,
        vi_mode=vi_mode,
        history_filename=history_filename,
        startup_paths=startup_paths,
        quit_words=quit_words,
    )

    if title:
        repl.terminal_title = title

    if configure:
        configure(repl)

    # Start repl.
    patch_context: ContextManager = (
        patch_stdout_context() if patch_stdout else DummyContext()
    )

    if return_asyncio_coroutine:

        async def coroutine():
            with patch_context:
                await repl.run_async()

        return coroutine()
    else:
        with patch_context:
            repl.run()
