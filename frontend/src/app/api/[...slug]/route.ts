import { NextRequest, NextResponse } from 'next/server';

const handler = async (req: NextRequest) => {
  const { pathname, search } = new URL(req.url);
  const slug = pathname.replace(/^\/api/, '');
  const internalApiUrl = `${process.env.INTERNAL_API_BASE_URL}${slug}${search}`;

  try {
    const response = await fetch(internalApiUrl, {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
        // Forward any other headers if necessary
      },
      body: req.body,
    });

    return new NextResponse(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  } catch (error) {
    console.error('API proxy error:', error);
    return new NextResponse('API proxy error', { status: 500 });
  }
};

export { handler as GET, handler as POST, handler as PUT, handler as DELETE };