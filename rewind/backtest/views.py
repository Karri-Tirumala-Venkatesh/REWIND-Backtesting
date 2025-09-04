import os
import subprocess
import tempfile
import uuid
import shutil

from django.shortcuts import render
from django.conf import settings
from django.utils.text import slugify

import google.generativeai as genai

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyDGXqAPlUm-KYoLmk0R69sFoyhLUTYlXz4")
genai.configure(api_key=GOOGLE_API_KEY)

def _generate_strategy_code(strategy_description: str) -> str:
    try:
        import google.genai as genai
        from google.genai import types

        api_key = GOOGLE_API_KEY
        client = genai.Client(api_key=api_key)
        model = "gemini-1.5-flash"

        prompt = (
            "Convert the following backtesting strategy to ready-to-run Python code. "
            "Use yfinance for data and backtrader for backtesting. "
            "Import all necessary libraries. "
            "After downloading data with yfinance, flatten MultiIndex columns if present. "
            "Keep only 'Open', 'High', 'Low', 'Close', 'Volume'. "
            "Run the backtest, print statistics, and plot results. "
            "Only output Python code, no explanations.\n"
            f"{strategy_description}\n"
        )

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        config = types.GenerateContentConfig(temperature=0.35, response_mime_type="text/plain")

        code_chunks = []
        for chunk in client.models.generate_content_stream(model=model, contents=contents, config=config):
            code_chunks.append(chunk.text)
        python_code = "".join(code_chunks).strip()

        if python_code.startswith("```python"):
            python_code = python_code[len("```python"):].strip()
        if python_code.endswith("```"):
            python_code = python_code[:-len("```")].strip()

        return python_code or "# Error: No code generated."
    except Exception as e:
        return f"# Error: {e}"

def index(request):
    """
    Renders the index page.
    """
    return render(request, "backtest/index.html")



def strategy(request):
    """
    Handles the strategy form: generates code or saves the strategy.
    """
    if request.method == 'POST':
        strategy_name = request.POST.get('strategy_name', '').strip() or "Untitled Strategy"
        buy_condition = request.POST.get('buy_condition', '').strip()
        sell_condition = request.POST.get('sell_condition', '').strip()
        indicators = request.POST.get('indicators', '').strip()
        position_sizing = request.POST.get('position_sizing', '').strip()
        initial_cash = request.POST.get('initial_cash', '').strip()
        commission = request.POST.get('commission', '').strip()
        data_source = request.POST.get('data_source', '').strip()
        stop_loss = request.POST.get('stop_loss', '').strip()
        other_constraints = request.POST.get('other_constraints', '').strip()
        notes = request.POST.get('notes', '').strip()

        strategy_text = (
            f"Strategy Name: {strategy_name}\n"
            f"Buy Condition: {buy_condition or 'Not specified'}\n"
            f"Sell Condition: {sell_condition or 'Not specified'}\n"
            f"Indicators: {indicators or 'Not specified'}\n"
            f"Position Sizing: {position_sizing or 'Not specified'}\n"
            f"Initial Cash: {initial_cash or 'Not specified'}\n"
            f"Commission: {commission or 'Not specified'}\n"
            f"Data Source: {data_source or 'Not specified'}\n"
            f"Stop Loss: {stop_loss or 'Not specified'}\n"
            f"Other Constraints: {other_constraints or 'None'}\n"
            f"Notes: {notes or 'None'}"
        )

        if not buy_condition and not sell_condition:
            return render(request, 'backtest/strategy.html', {'error': 'Buy or Sell Condition must be provided.'})

        python_code = _generate_strategy_code(strategy_text)

        temp_dir = tempfile.mkdtemp()
        code_path = os.path.join(temp_dir, f"{slugify(strategy_name)}.py")
        plot_path = os.path.join(settings.MEDIA_ROOT, f"{uuid.uuid4()}.png")
        report = ""
        try:
            python_code_mod = python_code.replace(
                "plt.show()",
                f"plt.savefig(r'{plot_path}'); plt.close()"
            )
            with open(code_path, "w", encoding="utf-8") as f:
                f.write(python_code_mod)
            result = subprocess.run(
                ["python", code_path],
                capture_output=True,
                text=True,
                timeout=120
            )
            report = result.stdout + ("\n" + result.stderr if result.stderr else "")
        except Exception as e:
            report = f"Error running backtest: {e}"
            plot_path = None
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        plot_url = os.path.relpath(plot_path, settings.MEDIA_ROOT) if plot_path and os.path.exists(plot_path) else None
        return render(request, 'backtest/backtest_results.html', {
            'strategy_name': strategy_name,
            'report': report,
            'plot_url': plot_url,
            'code': python_code,
        })

    return render(request, 'backtest/strategy.html')
