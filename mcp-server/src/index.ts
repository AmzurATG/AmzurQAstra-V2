import dotenv from 'dotenv'
import { createServer } from './server'
import { logger } from './utils/logger'

dotenv.config()

const PORT = parseInt(process.env.PORT || '3001', 10)
const HOST = process.env.HOST || '0.0.0.0'

async function main() {
  try {
    const app = await createServer()
    
    app.listen(PORT, HOST, () => {
      logger.info(`QAstra MCP Server running on http://${HOST}:${PORT}`)
      logger.info('Available endpoints:')
      logger.info('  POST /mcp/execute - Execute browser actions')
      logger.info('  POST /mcp/screenshot - Capture screenshot')
      logger.info('  GET  /mcp/sessions - List active sessions')
      logger.info('  POST /mcp/sessions - Create new session')
      logger.info('  DELETE /mcp/sessions/:id - Close session')
    })
  } catch (error) {
    logger.error('Failed to start MCP server:', error)
    process.exit(1)
  }
}

main()
