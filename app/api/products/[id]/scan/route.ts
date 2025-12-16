import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { scraper } from '@/lib/scraper'

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Verify product belongs to user
    const product = await prisma.product.findFirst({
      where: {
        id: params.id,
        store: {
          userId: session.user.id
        }
      }
    })

    if (!product) {
      return NextResponse.json({ error: 'Product not found' }, { status: 404 })
    }

    // Scrape market data
    const scrapedPrices = await scraper.scrapeAllSources(product.name, product.category)
    
    if (scrapedPrices.length === 0) {
      return NextResponse.json(
        { error: 'No market data found' },
        { status: 404 }
      )
    }

    // Save market data to database
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

    // Calculate average competitor price
    const avgPrice = scraper.calculateAveragePrice(scrapedPrices)
    const priceRange = scraper.getPriceRange(scrapedPrices)

    // Update product with competitor price
    if (avgPrice) {
      await prisma.product.update({
        where: { id: product.id },
        data: { competitorPrice: avgPrice }
      })
    }

    return NextResponse.json({
      success: true,
      averagePrice: avgPrice,
      priceRange,
      sources: scrapedPrices.length
    })
  } catch (error) {
    console.error('Error scanning prices:', error)
    return NextResponse.json(
      { error: 'Failed to scan prices' },
      { status: 500 }
    )
  }
}

