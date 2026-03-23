import { Router, Request, Response, NextFunction } from 'express'
import { BrowserManager, CreateSessionOptions } from '../core/browserManager'

export function createSessionRoutes(browserManager: BrowserManager): Router {
  const router = Router()

  // List all sessions
  router.get('/', (req: Request, res: Response) => {
    const sessions = browserManager.listSessions()
    res.json({ sessions })
  })

  // Create new session
  router.post('/', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const options: CreateSessionOptions = req.body

      const session = await browserManager.createSession(options)

      res.status(201).json({
        id: session.id,
        browserType: session.browserType,
        createdAt: session.createdAt,
      })
    } catch (error) {
      next(error)
    }
  })

  // Get session details
  router.get('/:id', (req: Request, res: Response) => {
    const session = browserManager.getSession(req.params.id)
    
    if (!session) {
      return res.status(404).json({ error: 'Session not found' })
    }

    res.json({
      id: session.id,
      browserType: session.browserType,
      createdAt: session.createdAt,
      lastActivity: session.lastActivity,
    })
  })

  // Close session
  router.delete('/:id', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const closed = await browserManager.closeSession(req.params.id)
      
      if (!closed) {
        return res.status(404).json({ error: 'Session not found' })
      }

      res.status(204).send()
    } catch (error) {
      next(error)
    }
  })

  return router
}
