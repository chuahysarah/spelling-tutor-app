def render_hanzi_animations(word: str) -> None:
    """Renders interactive Hanzi Writer stroke animations for all Chinese characters in a sentence or phrase."""
    chinese_chars = [char for char in word if re.search(r"[\u3400-\u9fff]", char)]
    if not chinese_chars:
        return

    targets = ""
    scripts = ""
    
    for i, char in enumerate(chinese_chars):
        div_id = f"target-{i}-{ord(char)}"
        targets += f'<div id="{div_id}" style="display:inline-block; margin: 4px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fafafa;"></div>'
        scripts += f"""
        HanziWriter.create('{div_id}', '{char}', {{
            width: 100,
            height: 100,
            padding: 5,
            showOutline: true,
            strokeAnimationSpeed: 1,
            delayBetweenStrokes: 150
        }}).loopCharacterAnimation();
        """

    # Dynamically calculate container height based on total characters (rows of 5)
    chars_per_row = 5
    num_rows = (len(chinese_chars) + chars_per_row - 1) // chars_per_row
    container_height = num_rows * 120 + 20

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <script src="https://cdn.jsdelivr.net/npm/hanzi-writer@3.5/dist/hanzi-writer.min.js"></script>
    </head>
    <body style="margin: 0; padding: 0; background: transparent;">
      <div style="display: flex; flex-wrap: wrap; gap: 6px;">
        {targets}
      </div>
      <script>
        {scripts}
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=container_height)
