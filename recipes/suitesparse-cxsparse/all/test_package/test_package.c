#include <cs.h>

#include <stdio.h>

int main(void)
{
    /* 2x2 matrix [4 1; 1 3] in triplet form, solved with a Cholesky factorization. */
    cs_di *T = cs_di_spalloc(2, 2, 4, 1, 1);
    cs_di_entry(T, 0, 0, 4.0);
    cs_di_entry(T, 1, 0, 1.0);
    cs_di_entry(T, 0, 1, 1.0);
    cs_di_entry(T, 1, 1, 3.0);
    cs_di *A = cs_di_compress(T);
    cs_di_spfree(T);

    double b[2] = {1.0, 2.0};
    int ok = cs_di_cholsol(1, A, b);
    cs_di_spfree(A);

    printf("CXSparse %d.%d.%d: x = [%g, %g]\n", CS_VER, CS_SUBVER, CS_SUBSUB, b[0], b[1]);
    return ok ? 0 : 1;
}
