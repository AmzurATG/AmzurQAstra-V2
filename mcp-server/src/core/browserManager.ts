import { chromium, firefox, webkit, Browser, BrowserContext, Page } from 'playwright'
import { v4 as uuidv4 } from 'uuid'
import { logger } from '../utils/logger'

export type BrowserType = 'chromium' | 'firefox' | 'webkit'

export interface BrowserSession {
  id: string
  browserType: BrowserType
  browser: Browser
  context: BrowserContext
  page: Page
  createdAt: Date
  lastActivity: Date
}

export interface CreateSessionOptions {
  browserType?: BrowserType
  headless?: boolean
  viewport?: { width: number; height: number }
  userAgent?: string
  timeout?: number
}

export class BrowserManager {
  private sessions: Map<string, BrowserSession> = new Map()
  private defaultTimeout = 30000

  async initialize(): Promise<void> {
    // Ensure browsers are downloaded
    logger.info('Verifying Playwright browsers...')
  }

  async createSession(options: CreateSessionOptions = {}): Promise<BrowserSession> {
    const {
      browserType = 'chromium',
      headless = false,  // Default to visible browser for debugging
      viewport = { width: 1280, height: 720 },
      userAgent,
      timeout = this.defaultTimeout,
    } = options

    logger.info(`Creating session with headless=${headless}, browserType=${browserType}`)

    const browserLauncher = this.getBrowserLauncher(browserType)
    
    const browser = await browserLauncher.launch({
      headless,
      timeout,
    })

    const contextOptions: any = {
      viewport,
      ignoreHTTPSErrors: true,
    }
    
    if (userAgent) {
      contextOptions.userAgent = userAgent
    }

    const context = await browser.newContext(contextOptions)
    const page = await context.newPage()

    const session: BrowserSession = {
      id: uuidv4(),
      browserType,
      browser,
      context,
      page,
      createdAt: new Date(),
      lastActivity: new Date(),
    }

    this.sessions.set(session.id, session)
    logger.info(`Created browser session: ${session.id} (${browserType})`)

    return session
  }

  getSession(sessionId: string): BrowserSession | undefined {
    return this.sessions.get(sessionId)
  }

  listSessions(): Array<{ id: string; browserType: BrowserType; createdAt: Date; lastActivity: Date }> {
    return Array.from(this.sessions.values()).map((s) => ({
      id: s.id,
      browserType: s.browserType,
      createdAt: s.createdAt,
      lastActivity: s.lastActivity,
    }))
  }

  updateActivity(sessionId: string): void {
    const session = this.sessions.get(sessionId)
    if (session) {
      session.lastActivity = new Date()
    }
  }

  async closeSession(sessionId: string): Promise<boolean> {
    const session = this.sessions.get(sessionId)
    if (!session) {
      return false
    }

    try {
      await session.context.close()
      await session.browser.close()
      this.sessions.delete(sessionId)
      logger.info(`Closed browser session: ${sessionId}`)
      return true
    } catch (error) {
      logger.error(`Error closing session ${sessionId}:`, error)
      this.sessions.delete(sessionId)
      return false
    }
  }

  async closeAll(): Promise<void> {
    const sessionIds = Array.from(this.sessions.keys())
    await Promise.all(sessionIds.map((id) => this.closeSession(id)))
    logger.info('All browser sessions closed')
  }

  private getBrowserLauncher(type: BrowserType) {
    switch (type) {
      case 'chromium':
        return chromium
      case 'firefox':
        return firefox
      case 'webkit':
        return webkit
      default:
        return chromium
    }
  }
}
