using System;
using System.IO;

namespace Sanic.Ppp.Spike.Plantilla.Tests
{
    /// <summary>
    /// Envuelve un MemoryStream pero se comporta como un stream de red tipico: no soporta
    /// seek y consultar Length revienta. Para probar que LP-02 nunca depende de esas dos
    /// cosas (el revisor encontro que el chequeo por Length se salteaba entero con esto).
    /// </summary>
    internal sealed class StreamNoConfiable : Stream
    {
        private readonly MemoryStream _interno;

        public StreamNoConfiable(byte[] datos)
        {
            _interno = new MemoryStream(datos, writable: false);
        }

        public override bool CanRead => true;
        public override bool CanSeek => false;
        public override bool CanWrite => false;
        public override long Length => throw new NotSupportedException("Length no disponible en este stream.");

        public override long Position
        {
            get => throw new NotSupportedException();
            set => throw new NotSupportedException();
        }

        public override int Read(byte[] buffer, int offset, int count) => _interno.Read(buffer, offset, count);
        public override void Flush() { }
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();

        protected override void Dispose(bool disposing)
        {
            if (disposing) _interno.Dispose();
            base.Dispose(disposing);
        }
    }
}
