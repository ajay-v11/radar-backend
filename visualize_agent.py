import sys
import os

# Add the current directory to sys.path to ensure we can import the module
sys.path.append(os.getcwd())

try:
    from agents.industry_detection_agent.graph import get_industry_detector_graph
except ImportError:
    # If running from inside the agents directory, try adjusting path
    sys.path.append(os.path.dirname(os.path.dirname(os.getcwd())))
    from agents.industry_detection_agent.graph import get_industry_detector_graph

def main():
    print("Generating graph visualization...")
    try:
        # Get the compiled graph
        graph = get_industry_detector_graph()
        
        # Generate the PNG
        # Note: This might require internet access to hit the mermaid.ink API
        # or local dependencies for graph generation.
        png_bytes = graph.get_graph().draw_mermaid_png()
        
        output_file = "industry_detection_graph.png"
        with open(output_file, "wb") as f:
            f.write(png_bytes)
            
        print(f"Success! Graph visualization saved to {output_file}")
        
    except Exception as e:
        print(f"Error generating PNG: {e}")
        print("\nFalling back to Mermaid syntax. You can paste this into https://mermaid.live/ :\n")
        try:
            print(graph.get_graph().draw_mermaid())
        except Exception as e2:
            print(f"Error generating Mermaid syntax: {e2}")

if __name__ == "__main__":
    main()
