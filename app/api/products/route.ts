import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const storeId = searchParams.get('storeId')

    const where: any = {
      store: {
        userId: session.user.id
      }
    }

    if (storeId) {
      where.storeId = storeId
    }

    const products = await prisma.product.findMany({
      where,
      include: {
        store: true
      },
      orderBy: {
        createdAt: 'desc'
      }
    })

    return NextResponse.json(products)
  } catch (error) {
    console.error('Error fetching products:', error)
    return NextResponse.json(
      { error: 'Failed to fetch products' },
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
    const { storeId, name, sku, category, costPrice, currentPrice, competitorPrice, salesVelocity } = body

    // Verify store belongs to user
    const store = await prisma.store.findFirst({
      where: {
        id: storeId,
        userId: session.user.id
      }
    })

    if (!store) {
      return NextResponse.json({ error: 'Store not found' }, { status: 404 })
    }

    const product = await prisma.product.create({
      data: {
        storeId,
        name,
        sku,
        category: category || 'Other',
        costPrice: parseFloat(costPrice),
        currentPrice: parseFloat(currentPrice),
        competitorPrice: competitorPrice ? parseFloat(competitorPrice) : null,
        salesVelocity: salesVelocity ? parseFloat(salesVelocity) : 0,
      }
    })

    return NextResponse.json(product)
  } catch (error) {
    console.error('Error creating product:', error)
    return NextResponse.json(
      { error: 'Failed to create product' },
      { status: 500 }
    )
  }
}

