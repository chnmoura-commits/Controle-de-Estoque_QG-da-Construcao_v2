/* Tema de cores e fontes do sistema (Tailwind).
   Definido antes do script de inicialização. */
tailwind.config = {
    theme: {
        extend: {
            colors: {
                vermelhao: {
                    10: '#FBFAF8', 20: '#FAF7F5', 30: '#F7F2EF', 40: '#F4EDE8',
                    50: '#F1E7E0', 60: '#EEE0D7', 70: '#E9D6C9', 80: '#E4CCBA',
                    90: '#DFC0A9', 100: '#D8B092', 110: '#DD9D6C', 120: '#C28E66',
                    130: '#B67D50', 140: '#9F6C45', 150: '#835B3B', 160: '#694A31',
                    170: '#503A27', 180: '#3C2C1F', 190: '#2B2017',
                },
                danger: {
                    50: '#FBF0EE', 100: '#F5E0DC', 200: '#EBC4BD', 300: '#DBA096',
                    400: '#C97468', 500: '#B5483D', 600: '#A03D33', 700: '#87322A',
                    800: '#6E2922', 900: '#57201B',
                },
                success: {
                    50: '#EFF4EE', 100: '#E3EBE1', 200: '#C7D8C4', 300: '#A2BC9E',
                    400: '#7E9C79', 500: '#5E7C5A', 600: '#4F684B', 700: '#41553D',
                    800: '#344430', 900: '#293526',
                },
                info: {
                    50: '#EEF2F5', 100: '#E1E8EC', 200: '#C3D2DA', 300: '#9AB1BD',
                    400: '#718D9C', 500: '#5B7B8C', 600: '#4C6776', 700: '#3F5460',
                    800: '#33434D', 900: '#28353D',
                },
                warn: {
                    50: '#F7F1EB', 100: '#F1E4D8', 200: '#E4CCBA', 300: '#D6B393',
                    400: '#C8996C', 500: '#B67D50', 600: '#9F6C45', 700: '#835B3B',
                    800: '#694A31', 900: '#503A27',
                },
            },
            fontFamily: {
                sans: ['Barlow', 'system-ui', 'sans-serif'],
                display: ['"Barlow Semi Condensed"', 'Barlow', 'sans-serif'],
            }
        }
    }
};
