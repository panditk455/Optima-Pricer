import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

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

    // Verify recommendation belongs to user
    const recommendation = await prisma.recommendation.findFirst({
      where: {
        id: params.id,
        product: {
          store: {
            userId: session.user.id
          }
        }
      },
      include: {
        product: true
      }
    })

    if (!recommendation) {
      return NextResponse.json({ error: 'Recommendation not found' }, { status: 404 })
    }

    // If applying recommendation, update product price
    if (body.status === 'applied' && body.applyPrice) {
      await prisma.product.update({
        where: { id: recommendation.productId },
        data: { currentPrice: recommendation.suggestedPrice }
      })
    }

    // Update recommendation
    const updateData: any = {}
    if (body.status !== undefined) updateData.status = body.status

    const updated = await prisma.recommendation.update({
      where: { id: params.id },
      data: updateData,
      include: {
        product: {
          include: {
            store: true
          }
        }
      }
    })

    return NextResponse.json(updated)
  } catch (error) {
    console.error('Error updating recommendation:', error)
    return NextResponse.json(
      { error: 'Failed to update recommendation' },
      { status: 500 }
    )
  }
}

