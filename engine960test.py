import chess.engine

# Start engine
engine = chess.engine.SimpleEngine.popen_uci(r"C:\Users\Rfair\Downloads\original-960-gui\engines\stockfish-windows-x86-64-avx2.exe")  # replace with your actual path

# Check for UCI_Chess960 support
supports_chess960 = "UCI_Chess960" in engine.options
option_type = type(engine.options.get("UCI_Chess960")).__name__ if supports_chess960 else "Not available"

print("Supports UCI_Chess960:", supports_chess960)
print("Type of UCI_Chess960 option:", option_type)

engine.quit()
