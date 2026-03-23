import express, { Express } from 'express'
import cors from 'cors'
import { BrowserManager } from './core/browserManager'
import { createMcpRoutes } from './routes/mcp'
import { createSessionRoutes } from './routes/sessions'
import { errorHandler } from './middleware/errorHandler'
import { requestLogger } from './middleware/requestLogger'
import { logger } from './utils/logger'

export async function createServer(): Promise<Express> {
  const app = express()
  
  // Initialize browser manager
  const browserManager = new BrowserManager()
  await browserManager.initialize()
  logger.info('Browser manager initialized')

  // Middleware
  app.use(cors())
  app.use(express.json())
  app.use(requestLogger)

  // Health check
  app.get('/health', (_, res) => {
    res.json({ status: 'healthy', timestamp: new Date().toISOString() })
  })

  // Routes
  app.use('/mcp', createMcpRoutes(browserManager))
  app.use('/mcp/sessions', createSessionRoutes(browserManager))

  // Error handling
  app.use(errorHandler)

  // Graceful shutdown
  process.on('SIGTERM', async () => {
    logger.info('SIGTERM received, closing browser sessions...')
    await browserManager.closeAll()
    process.exit(0)
  })

  return app
}
