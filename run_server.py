#!/usr/bin/env python
import sys
sys.path.insert(0, 'src')
if __name__ == '__main__':
    import uvicorn
    from src.api.app import create_app
    app = create_app()
    uvicorn.run(app, host='0.0.0.0', port=8001)