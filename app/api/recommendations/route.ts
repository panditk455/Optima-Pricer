import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { priceOptimizer } from '@/lib/price-optimizer'
import { scraper } from '@/lib/scraper'

export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const status = searchParams.get('status')
    const productId = searchParams.get('productId')

    const where: any = {
      product: {
        store: {
          userId: session.user.id
        }
      }
    }

    if (status) {
      where.status = status
    }

    if (productId) {
      where.productId = productId
    }

    const recommendations = await prisma.recommendation.findMany({
      where,
      include: {
        product: {
          include: {
            store: true
          }
        }
      },
      orderBy: {
        createdAt: 'desc'
      }
    })

    return NextResponse.json(recommendations)
  } catch (error) {
    console.error('Error fetching recommendations:', error)
    return NextResponse.json(
      { error: 'Failed to fetch recommendations' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { productId } = body

    // Verify product belongs to user
    const product = await prisma.product.findFirst({
      where: {
        id: productId,
        store: {
          userId: session.user.id
        }
      }
    })

    if (!product) {
      return NextResponse.json({ error: 'Product not found' }, { status: 404 })
    }

    // Check if pending recommendation already exists
    const existingRec = await prisma.recommendation.findFirst({
      where: {
        productId,
        status: 'pending'
      }
    })

    if (existingRec) {
      return NextResponse.json(existingRec)
    }

    // Get recent market data
    const recentMarketData = await prisma.marketData.findMany({
      where: {
        productId,
        scrapedAt: {
          gte: new Date(Date.now() - 24 * 60 * 60 * 1000) // Last 24 hours
        }
      }
    })

    let competitorPrices: number[] = []
    if (recentMarketData.length > 0) {
      competitorPrices = recentMarketData.map(md => md.price)
    } else if (product.competitorPrice) {
      // Use stored competitor price if no recent market data
      competitorPrices = [product.competitorPrice]
    }

    // If no competitor data, scrape it
    if (competitorPrices.length === 0) {
      const scrapedPrices = await scraper.scrapeAllSources(product.name, product.category)
      competitorPrices = scrapedPrices.map(sp => sp.price)
      
      // Save scraped data
      if (scrapedPrices.length > 0) {
        await Promise.all(
          scrapedPrices.map(priceData =>
            prisma.marketData.create({
              data: {
                productId: product.id,
                source: priceData.source,
                price: priceData.price,
                url: priceData.url
              }
            })
          )
        )
      }
    }

    // Calculate price range
    const priceRange = competitorPrices.length > 0
      ? {
          min: Math.min(...competitorPrices),
          max: Math.max(...competitorPrices),
          average: competitorPrices.reduce((a, b) => a + b, 0) / competitorPrices.length
        }
      : undefined

    // Generate optimization
    const optimization = priceOptimizer.optimizePrice({
      product: {
        id: product.id,
        name: product.name,
        sku: product.sku,
        category: product.category as any,
        cost_price: product.costPrice,
        current_price: product.currentPrice,
        competitor_price: product.competitorPrice || undefined,
        sales_velocity: product.salesVelocity
      },
      competitorPrices,
      marketData: priceRange
    })

    // Create recommendation
    const recommendation = await prisma.recommendation.create({
      data: {
        productId,
        suggestedPrice: optimization.suggestedPrice,
        predictedMargin: optimization.predictedMargin,
        confidenceScore: optimization.confidenceScore,
        rationale: optimization.rationale,
        status: 'pending',
        riskLevel: optimization.riskLevel,
        competitorMinPrice: optimization.competitorMinPrice,
        competitorMaxPrice: optimization.competitorMaxPrice,
        marketPosition: optimization.marketPosition,
        strategy: optimization.strategy,
        implementationTiming: optimization.implementationTiming,
        revenueImpact: optimization.revenueImpact
      },
      include: {
        product: {
          include: {
            store: true
          }
        }
      }
    })

    return NextResponse.json(recommendation)
  } catch (error) {
    console.error('Error creating recommendation:', error)
    return NextResponse.json(
      { error: 'Failed to create recommendation' },
      { status: 500 }
    )
  }
}

