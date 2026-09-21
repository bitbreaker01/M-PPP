using System;
using System.IO;

namespace Sanic.Mppp.Plugins.Plantilla
{
    /// <summary>Lector sobre Open XML SDK 3.1.0. Reglas LP-01 a LP-08 de diseno/03 §7.</summary>
    public sealed class LectorOpenXml : ILectorPlantilla
    {
        public LectorOpenXml()
            : this(new LimitesLectura())
        {
        }

        public LectorOpenXml(LimitesLectura limites)
        {
            throw new NotImplementedException();
        }

        public ResultadoLecturaPlantilla Leer(Stream excel, ConfiguracionPlantilla configuracion)
        {
            throw new NotImplementedException();
        }

        public ResultadoLecturaPlantilla Leer(byte[] excel, ConfiguracionPlantilla configuracion)
        {
            throw new NotImplementedException();
        }
    }
}
