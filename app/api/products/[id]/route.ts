import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const product = await prisma.product.findFirst({
      where: {
        id: params.id,
        store: {
          userId: session.user.id
        }
      },
      include: {
        store: true
      }
    })

    if (!product) {
      return NextResponse.json({ error: 'Product not found' }, { status: 404 })
    }

    return NextResponse.json(product)
  } catch (error) {
    console.error('Error fetching product:', error)
    return NextResponse.json(
      { error: 'Failed to fetch product' },
      { status: 500 }
    )
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()

    // Verify product belongs to user
    const existingProduct = await prisma.product.findFirst({
      where: {
        id: params.id,
        store: {
          userId: session.user.id
        }
      }
    })

    if (!existingProduct) {
      return NextResponse.json({ error: 'Product not found' }, { status: 404 })
    }

    const updateData: any = {}
    if (body.costPrice !== undefined) updateData.costPrice = parseFloat(body.costPrice)
    if (body.currentPrice !== undefined) updateData.currentPrice = parseFloat(body.currentPrice)
    if (body.competitorPrice !== undefined) updateData.competitorPrice = body.competitorPrice ? parseFloat(body.competitorPrice) : null
    if (body.salesVelocity !== undefined) updateData.salesVelocity = parseFloat(body.salesVelocity)
    if (body.name !== undefined) updateData.name = body.name
    if (body.sku !== undefined) updateData.sku = body.sku
    if (body.category !== undefined) updateData.category = body.category

    const product = await prisma.product.update({
      where: { id: params.id },
      data: updateData
    })

    return NextResponse.json(product)
  } catch (error) {
    console.error('Error updating product:', error)
    return NextResponse.json(
      { error: 'Failed to update product' },
      { status: 500 }
    )
  }
}

export async function DELETE(
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

    await prisma.product.delete({
      where: { id: params.id }
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting product:', error)
    return NextResponse.json(
      { error: 'Failed to delete product' },
      { status: 500 }
    )
  }
}

