package common

import "encoding/binary"

const MAX_LENGTH = 512
const MSG_LEN_SIZE = 2

func EncodeBet(bet Bet) ([]byte, uint16) {
	encoded := make([]byte, 0, MAX_LENGTH)

	encoded = append(encoded, encodeString(bet.Name)...)
	encoded = append(encoded, encodeString(bet.Surname)...)
	encoded = append(encoded, encodeInt(bet.Dni)...)
	encoded = append(encoded, []byte(bet.Birth)...)
	encoded = append(encoded, encodeInt(bet.Number)...)
	msgLen := uint16(len(encoded))
	encoded = append(encoded, encodeShort(msgLen)...)

	return encoded, msgLen + MSG_LEN_SIZE
}

func encodeString(s string) []byte {
	bytes := []byte(s)
	encoded := make([]byte, len(bytes)+1)
	encoded[0] = byte(len(bytes))
	copy(encoded[1:], bytes)
	return encoded
}

func encodeInt(i uint32) []byte {
	bytes := make([]byte, 4)
	binary.BigEndian.PutUint32(bytes, uint32(i))
	return bytes
}

func encodeShort(i uint16) []byte {
	bytes := make([]byte, 2)
	binary.BigEndian.PutUint16(bytes, i)
	return bytes
}
